#!/usr/bin/env python3

import socket
import selectors
import traceback
import lib_for_http_server as lib_helper
import os
import argparse
import threading
import logging


class MultiprocessSocketServer:

    def __init__(self, host="", port=80, workers=5, timeout=3, rootdir=os.path.abspath("./doc_root")):
        self.host = host
        self.port = port
        self.workers = workers
        self.rootdir = rootdir
        self.threads = []
        self.timeout = timeout

    def worker(self, lsock, stop):
        sel = selectors.DefaultSelector()
        sel.register(lsock, selectors.EVENT_READ, data=None)
        while not stop.is_set():
            events = sel.select(timeout=self.timeout)
            for key, mask in events:
                if key.data is None:
                    self.accept_wrapper(key.fileobj, sel)
                else:
                    message = key.data
                    try:
                        message.process_events(mask)
                    except Exception:
                        logging.debug(
                            f'main: error: exception for {message.addr}:\n{traceback.format_exc()}')
                        message.close()
        sel.close()

    def accept_wrapper(self, sock, sel):
        rootdir = self.rootdir
        try:
            conn, addr = sock.accept()  # Should be ready to read
        except BlockingIOError:
            return
        logging.debug(f'accepted connection from {addr}')
        conn.setblocking(False)
        message = lib_helper.Message(sel, conn, addr, rootdir)
        sel.register(conn, selectors.EVENT_READ, data=message)

    def serve_forever(self):
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind((self.host, self.port))
        lsock.listen()
        logging.debug('listening on %s %s' % (self.host, self.port))
        stop = threading.Event()
        for _ in range(self.workers):
            t = threading.Thread(target=self.worker, args=(lsock, stop))
            t.start()
            self.threads.append(t)
        # Джойнимся явно (ждем завершения потоков)
        logging.debug(f'Number of Threads {len(self.threads)}')
        try:
            for t in self.threads:
                t.join(self.timeout + 1)
        except KeyboardInterrupt:
            stop.set()
            logging.debug('Shutting down server...')
            for t in self.threads:
                t.join(self.timeout + 1)
                logging.debug(f'Worker {t.name} was stopped')


def parse_args():
    parser = argparse.ArgumentParser(description='OTUServer')
    parser.add_argument(
        '-hs', '--host', type=str, default="localhost",
        help='listened host, default - localhost'
    )
    parser.add_argument(
        '-p', '--port', type=int, default=80,
        help='listened port, default - 80'
    )
    parser.add_argument(
        '-w', '--workers', type=int, default=5,
        help='server workers count, default - 5'
    )
    parser.add_argument(
        '-r', '--root', type=str, default='doc_root',
        help='DIRECTORY_ROOT with site files, default - doc_root'
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    config = {
                "REPORT_LOG": None,
                "DEBUG": True
              }
    logging.basicConfig(filename=config.get("REPORT_LOG", None),
                        level=logging.DEBUG if config.get("DEBUG", None) else logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    init_args = dict(host=args.host,
                     port=args.port,
                     workers=args.workers,
                     rootdir=args.root,
                     )
    server = MultiprocessSocketServer(**init_args)
    server.serve_forever()
