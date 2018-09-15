#!/usr/local/bin/python3
# -*- coding: utf-8; -*-

import unittest
import log_analyzer
from collections import namedtuple


class LogAnalyzerTests(unittest.TestCase):
    def test_median(self):
        # median of even list
        self.assertEqual(log_analyzer.median([1, 2, 3, 4, 5]), 3)
        # median of odd list
        self.assertEqual(log_analyzer.median([1, 2, 4, 5]), 3)
        # median of list with single element
        self.assertEqual(log_analyzer.median([1]), 1)

    def test_catchfile(self):
        Logfile = namedtuple('Logfile', 'path date ext')
        # test directory with test filenames
        # print(log_analyzer.catchfile("./test_log_files"))
        self.assertEqual(log_analyzer.catchfile("./test_log_files"),
                         Logfile(path='./test_log_files/nginx-access-ui.log-20180818.gz', date='20180818', ext='gz'))

    def test_nginx_log_parser(self):
        line1 = "1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] \"" \
                "GET /api/v2/banner/25019354 HTTP/1.1\"" \
                " 200 927 \"-\" \"Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5\"" \
                " \"-\" \"1498697422-2190034393-4708-9752759\" \"dc7161be3\" 0.390"
        # print(log_analyzer.nginx_log_parser(line1))
        self.assertEqual(log_analyzer.nginx_log_parser(line1),
                         {'request_url': '/api/v2/banner/25019354', 'response_time': 0.39})


if __name__ == "__main__":
    unittest.main()
