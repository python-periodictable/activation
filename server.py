#!/usr/bin/env python
"""
Simple server for running the neutron activation calculator.

This is intended for testing.  It has not been assessed for security and is
not recommended for a public facing server.  The activation calculator
expects a cgi interface, which should be provided by the web infrastructure
(apache, nginx, etc.) that you are using on your production server.

Usage: python server.py [host | host:port]

Default is localhost:8008
"""

from __future__ import print_function

import sys
import os
try:
    from http.server import HTTPServer, CGIHTTPRequestHandler
    from socketserver import ThreadingMixIn
except ImportError:
    from BaseHTTPServer import HTTPServer
    from SocketServer import ThreadingMixIn
    from CGIHTTPServer import CGIHTTPRequestHandler
import cgitb
cgitb.enable()  ## This line enables CGI error reporting

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Very simple threaded server"""
    allow_reuse_address = True
    request_queue_size = 50

server = ThreadedHTTPServer
handler = CGIHTTPRequestHandler
handler.cgi_directories = ["/cgi-bin"]

if len(sys.argv) > 1:
    host, *rest = sys.argv[1].split(':', 1)
    port = int(rest[0]) if rest else 8008
else:
    host, port = "", 8008
print(f"serving on http://{host}:{port}/activation/")
httpd = server((host, port), handler)
httpd.serve_forever()
