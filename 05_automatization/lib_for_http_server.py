import os
import selectors
import datetime
import mimetypes
import re
import logging


class Message:
    def __init__(self, selector, sock, addr, rootdir):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b''
        self._send_buffer = b''
        self.ac_in_buffer = b''
        self.incoming = []
        self.ac_in_buffer_size = 4096
        self.set_terminator(b"\r\n\r\n")
        self.method = None
        self.uri = None
        self.request = None
        self.response_created = False
        self.request_processor = HTTPRequestProcessor(rootdir)

    def set_terminator (self, term):
        "Set the input delimiter.  Can be a fixed string of any length, an integer, or None"
        self.terminator = term

    def get_terminator(self):
        return self.terminator

    # grab some more data from the socket,
    # throw it to the collector method,
    # check for the terminator,
    # if found, transition to the next state.
    def found_terminator(self):
        self._recv_buffer = self._get_data()

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == 'r':
            events = selectors.EVENT_READ
        elif mode == 'w':
            events = selectors.EVENT_WRITE
        elif mode == 'rw':
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f'Invalid events mask mode {repr(mode)}.')
        self.selector.modify(self.sock, events, data=self)

    def _read(self):
        # this func code from https://github.com/python/cpython/blob/2.7/Lib/asynchat.py#L112
        try:
            data = self.sock.recv(self.ac_in_buffer_size)
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:
                self.ac_in_buffer += data

        # Continue to search for self.terminator in self.ac_in_buffer,
        # while calling self.collect_incoming_data.  The while loop
        # is necessary because we might read several data+terminator
        # combos with a single recv(4096).

        while self.ac_in_buffer:
            lenbuff = len(self.ac_in_buffer)
            terminator = self.get_terminator()
            if not terminator:
                # no terminator, collect it all
                self.collect_incoming_data(self.ac_in_buffer)
                self.ac_in_buffer = b''
            elif isinstance(terminator, (int,)):
                # numeric terminator
                n = terminator
                if lenbuff < n:
                    self.collect_incoming_data(self.ac_in_buffer)
                    self.ac_in_buffer = b''
                    self.terminator = self.terminator - lenbuff
                else:
                    self.collect_incoming_data(self.ac_in_buffer[:n])
                    self.ac_in_buffer = self.ac_in_buffer[n:]
                    self.terminator = 0
                    self.found_terminator()
            else:
                # 3 cases:
                # 1) end of buffer matches terminator exactly:
                #    collect data, transition
                # 2) end of buffer matches some prefix:
                #    collect data to the prefix
                # 3) end of buffer does not match any prefix:
                #    collect data
                terminator_len = len(terminator)
                index = self.ac_in_buffer.find(terminator)
                if index != -1:
                    # we found the terminator
                    if index > 0:
                        # don't bother reporting the empty string (source of subtle bugs)
                        self.collect_incoming_data(self.ac_in_buffer[:index])
                    self.ac_in_buffer = self.ac_in_buffer[index + terminator_len:]
                    # This does the Right Thing if the terminator is changed here.
                    self.found_terminator()
                else:
                    # check for a prefix of the terminator
                    index = find_prefix_at_end(self.ac_in_buffer, terminator)
                    if index:
                        if index != lenbuff:
                            # we found a prefix, collect up to the prefix
                            self.collect_incoming_data(self.ac_in_buffer[:-index])
                            self.ac_in_buffer = self.ac_in_buffer[-index:]
                        break
                    else:
                        # no prefix, collect it all
                        self.collect_incoming_data(self.ac_in_buffer)
                        self.ac_in_buffer = b''

    def collect_incoming_data(self, data):
        self._collect_incoming_data(data)

    def _collect_incoming_data(self, data):
        self.incoming.append(data)

    def _get_data(self):
        d = b''.join(self.incoming)
        del self.incoming[:]
        return d

    def _write(self):
        if self._send_buffer:
            # print('sending', repr(self._send_buffer), 'to', self.addr)
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]
                # Close when the buffer is drained. The response has been sent.
                if sent and not self._send_buffer:
                    self.close()

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        self._read()
        if self.request is None:
            self.process_request()

    def write(self):
        if self.request:
            if not self.response_created:
                self.create_response()
        self._write()

    def close(self):
        logging.debug(f'closing connection to {self.addr}')
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            logging.debug(f'error: selector.unregister() exception for {self.addr}: {repr(e)}')
            pass

        try:
            self.sock.close()
        except OSError as e:
            logging.debug(f'error: socket.close() exception for {self.addr}: {repr(e)}')
            pass
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None

    def process_request(self):
        self.request = self._recv_buffer
        logging.debug("request = %s" % self.request)
        self._set_selector_events_mask('w')

    def create_response(self):
        message = self._create_response(self.request)
        self.response_created = True
        self._send_buffer += message

    def _create_response(self, request):
        return self.request_processor.create_response_for_message(request)


class HTTPRequestProcessor:

    def __init__(self, rootdir):
        self.responsecode = {"200": "OK",
                             "500": "Internal sever Error",
                             "405": "Method Unsupported",
                             "403": "Forbidden",
                             "404": "Resource Not Fund",
                             }
        self.rootdir = rootdir
        # Date, Server, Content‐Length, Content‐Type, Connection
        self.headers = dict(Server='OTUServer')
        self.version = "HTTP/1.1"
        self.supported_methods = ["GET", "HEAD"]
        self.uri_pattern = re.compile(r"^\/[\/\.a-zA-Z0-9\-\_\%]*$")

    def create_response_for_message(self, request):
        try:
            processed_str = request.decode("utf-8")
        except UnicodeDecodeError:
            return self.create_response_not_200("500")
        method, uri, *_ = processed_str.split(" ")
        if method not in self.supported_methods:
            return self.create_response_not_200("405")
        if method.upper() == "GET":
            response = self.validate_uri(method, uri)
        else:
            response = self.validate_uri(method, uri)
        return response

    def create_response_not_200(self, responsecode):
        self._flush_headers()
        send_mesg = self._format_response_head(responsecode)
        with open(f"error_templates/{responsecode}.html", 'rb') as error_file:
            body = error_file.read()
        self.headers['Content-Length'] = self.get_file_size(f"error_templates/{responsecode}.html")
        self.headers['Content‐Type'] = mimetypes.guess_type(f"error_templates/{responsecode}.html")[0]
        self.headers['Connection'] = "close"
        response = send_mesg.encode("utf-8") + body
        logging.debug(f"Sended message {response}")
        return response

    def create_response_200(self, method, uri="error_templates/404.html"):
        # self._flush_headers()
        body = b""
        self.headers['Content-Length'] = self.get_file_size(uri)
        self.headers["Content-Type"] = mimetypes.guess_type(uri)[0]
        self.headers['Connection'] = "close"
        if method == "GET":
            with open(uri, "rb") as error_file:
                body = error_file.read()
        send_mesg = self._format_response_head("200")
        response = send_mesg.encode("utf-8") + body
        logging.debug(f"Sended message {response}")
        return response

    def validate_uri(self, method, uri):
        try:
            if "../" in uri:
                return self.create_response_not_200("403")
            # Split ? and #
            uri = uri.split("#")[0].split("?")[0]
            if not self.uri_pattern.match(uri):
                return self.create_response_not_200("403")
            # understand spaces и %XX in filename
            uri = self.unquote_uri(uri)
            uri = os.path.join(self.rootdir, uri.lstrip('/'))
            if os.path.isdir(uri):
                uri = os.path.join(uri, 'index.html')
            if not os.path.isfile(uri):
                return self.create_response_not_200("404")
            # print(uri)
            response = self.create_response_200(method=method, uri=uri)
            return response
        except Exception as e:
            # print(repr(e))
            return self.create_response_not_200("500")

    def _format_response_head(self, responsecode):
        response_string = self.responsecode[responsecode]
        version = self.version
        response_code_header_str = f'{" ".join([version, responsecode, response_string])}\r\n'
        headers = self._create_headers()
        if headers:
            response_code_header_str = f'{response_code_header_str}{headers}\r\n\r\n'
        return response_code_header_str

    def _create_headers(self):
        self.headers['Date'] = self._create_timestamp()
        temp_headers = [f'{key}: {value}' for key, value in self.headers.items()]
        headers = "\r\n".join(temp_headers)
        return headers

    @staticmethod
    def _create_timestamp():
        return datetime.datetime.strftime(datetime.datetime.now(), "%d %b %Y %H:%M")

    def _flush_headers(self):
        self.headers = dict(Server='OTUServer')

    @staticmethod
    def get_file_size(uri):
        return os.path.getsize(uri)

    @staticmethod
    def unquote_uri(uri):
        # from urllib.parse lightly changed
        _hexdig = '0123456789ABCDEFabcdef'
        _hextobyte = None
        if _hextobyte is None:
            _hextobyte = {
                ("%" + a + b).encode(): bytes([int(a + b, 16)])
                for a in _hexdig for b in _hexdig
            }
        uri_encoded = uri.encode()
        for match, sub in _hextobyte.items():
            uri_encoded = uri_encoded.replace(match, sub)
        return uri_encoded.decode(errors="replace")


# Given 'haystack', see if any prefix of 'needle' is at its end.  This
# assumes an exact match has already been checked.  Return the number of
# characters matched.
# for example:
# f_p_a_e ("qwerty\r", "\r\n") => 1
# f_p_a_e ("qwertydkjf", "\r\n") => 0
# f_p_a_e ("qwerty\r\n", "\r\n") => <undefined>

# this could maybe be made faster with a computed regex?
# [answer: no; circa Python-2.0, Jan 2001]
# new python:   28961/s
# old python:   18307/s
# re:        12820/s
# regex:     14035/s
def find_prefix_at_end(haystack, needle):
    length = len(needle) - 1
    while length and not haystack.endswith(needle[:length]):
        length -= 1
    return length
