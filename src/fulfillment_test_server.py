#!/usr/bin/env python3
"""
Sample of a python server to test building HTTP/REST/SOAP fulfillment targets

Use this to fine tune your request headers and body to debug any issues
before running it against your production systems.

Usage: fulfillment_test_server.py [port]
"""

import hashlib
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

# 0 or 1 indexed
DEFAULT_BASE_INDEX = 1
# total number of elements available
TOTAL_COUNT = 5
# number of retults to return if no page size is specified
MAX_PAGE_SIZE = TOTAL_COUNT


class State(object):
    """
    A place to keep stateful data
    """
    requests_total_count = 1
    records = []


def build_soap_content(ticket_id):
    """
    Build SOAP body
    """
    soap = f"""
<?xml version="1.0"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <soapenv:Body xmlns:m="http://www.myservice.com/incident">
        <m:insertResponse>
            <m:ticketNumber>{str(ticket_id)}</m:ticketNumber>
        </m:insertResponse>
    </soapenv:Body>
</soapenv:Envelope>
"""
    return soap


def build_json_content(path, request_id):
    """
    Build JSON body
    """
    u = urlparse(path)
    qs = parse_qs(u.query)
    base_index = int(qs['baseIndex'][0]
                     ) if 'base_index' in qs else DEFAULT_BASE_INDEX
    start_index = int(qs['startIndex'][0]
                      ) if 'startIndex' in qs else base_index
    page_size = int(qs['count'][0]) if 'count' in qs else MAX_PAGE_SIZE

    o = {
        'request': request_id,
        'baseIndex': base_index,
        'startIndex': start_index,
        'pageSize': page_size,
        'totalCount': TOTAL_COUNT,
        'results': []
    }

    # return at most page_size elements in response - not exeeding total element count
    for i in range(max(base_index, start_index), min(start_index + page_size, TOTAL_COUNT + base_index)):
        h = hashlib.sha256()
        h.update(str(i).encode('utf-8'))
        o['results'].append({'data': h.hexdigest(), 'id': i})

    body = json.dumps(o)
    return body


class FulFillmentRequestHandler(BaseHTTPRequestHandler):
    """
    Dump requests and send response
    """

    def do_GET(self):
        """
        HTTP GET handler
        """
        logging.info("GET request,\nPath: %s\nHeaders:\n%s",
                     str(self.path), str(self.headers))
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        body = build_json_content(self.path, State.requests_total_count)
        logging.info("Response body: \n%s", body)
        self.wfile.write(body.encode('utf-8'))
        State.requests_total_count = State.requests_total_count+1

    def do_POST(self):
        """
        HTTP POST handler
        """
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                     str(self.path), str(self.headers), post_data.decode('utf-8'))

        self.send_response(200)
        self.send_header('Content-type', 'text/xml')
        self.end_headers()
        body = build_soap_content(State.requests_total_count)
        logging.info("Response body: \n%s", body)
        self.wfile.write(body.encode('utf-8'))
        State.requests_total_count = State.requests_total_count+1


def run(server_class=HTTPServer, handler_class=FulFillmentRequestHandler, port=8080):
    """
    Run http server until interruped
    """
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd on %d...\n', httpd.server_port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopped httpd...\n')


if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
