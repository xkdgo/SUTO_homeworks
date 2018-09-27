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

    def __init__(self, host="", port=80, workers=5, rootdir=os.path.abspath("./doc_root")):
        self.host = host
        self.port = port
        self.workers = workers
        self.rootdir = rootdir


    def worker(self, lsock):
        sel = selectors.DefaultSelector()
        sel.register(lsock, selectors.EVENT_READ, data=None)
        try:
            while True:
                events = sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj, sel)
                    else:
                        message = key.data
                        try:
                            message.process_events(mask)
                        except Exception:
                            print('main: error: exception for',
                                  f'{message.addr}:\n{traceback.format_exc()}')
                            message.close()
        except KeyboardInterrupt:
            print('caught keyboard interrupt, exiting')
        finally:
            sel.close()

    def accept_wrapper(self, sock, sel):
        rootdir = self.rootdir
        try:
            conn, addr = sock.accept()  # Should be ready to read
        except BlockingIOError:
            return
        print('accepted connection from', addr)
        conn.setblocking(False)
        message = lib_helper.Message(sel, conn, addr, rootdir)
        sel.register(conn, selectors.EVENT_READ, data=message)

    def serve_forever(self):
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind((self.host, self.port))
        lsock.listen()
        print('listening on', (self.host, self.port))
        for _ in range(self.workers):
            t = threading.Thread(target=self.worker, args=(lsock,))
            t.start()


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
    init_args = dict(host=args.host,
                     port=args.port,
                     workers=args.workers,
                     rootdir=args.root)
    server = MultiprocessSocketServer(**init_args)
    server.serve_forever()
