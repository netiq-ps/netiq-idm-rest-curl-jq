#!/usr/bin/env python3
"""Fix issues in the NetIQ Identity Applications OpenAPI document.

This script fixes issues in swagger.json. It can also add security and server settings to make easily consumable by API tools such as Postman or Swagger.
"""

"""
MIT License

Copyright (c) 2021 Micro Focus

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


import requests
import json
import logging
from argparse import ArgumentParser
from typing import TYPE_CHECKING
log = logging.getLogger(__name__)
FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"


def main(args):
    """Runs program and handles command line options"""

    if args.loglevel:
        logging.basicConfig(level=args.loglevel or logging.INFO, format=FORMAT)
    else:
        logging.basicConfig(level=args.loglevel or logging.INFO)

    with open(args.file, "r") as read_file:
        spec = json.load(read_file)

    # include product name in title
    spec["info"]["title"] = "NetIQ Identity Applications REST API"

    # construct host field from hostname and port
    if (args.hostname is not None):
        spec["schemes"] = ["https"]
        # no port in URL for default https port number
        if (args.port is not None and args.port == "443"):
            spec["host"] = args.hostname
        else:
            spec["host"] = args.hostname + ":" + args.port

    # get OpenID provider meta data
    if (args.issuer is not None):
        meta_data_url = args.issuer + "/.well-known/openid-configuration"
        r = requests.get(meta_data_url)
        r.raise_for_status()
        meta_data = r.json()
        log.info("Successfully retrieved meta data from OpenID provider.")

        # add OAuth settings
        spec["securityDefinitions"] = {
            "oauth2-password": {
                "type": "oauth2",
                "description": "OAuth2 credential owner passwort grant",
                "tokenUrl": meta_data["token_endpoint"],
                "flow": "password",
                "scopes": {
                    "ism": "ism",
                }
            },
            "oauth2-accessCode": {
                "type": "oauth2",
                "description": "OAuth2 code grant",
                "authorizationUrl": meta_data["authorization_endpoint"],
                "tokenUrl": meta_data["token_endpoint"],
                "flow": "accessCode",
                "scopes": {
                    "ism": "ism",
                }
            }
        }
        spec["security"] = [{"oauth2-password": ["ism"]},
                            {"oauth2-accessCode": ["ism"]}]

    # The original base path is set to /IDMProv/rest/access. This is wrong for admin and catalog endpoints. Remove 3rd element from basePath and add it to individual paths instead.
    spec["basePath"] = "/IDMProv/rest"
    # Determine correct 3rd path element from endpoint"s tag and prepend it to existing path
    paths = {}
    for path in spec["paths"]:
        for method in spec["paths"][path]:
            tag = (spec["paths"][path][method]["tags"][0]).lower()
            paths["/" + tag + path] = {}
            # copy over method definition
            paths["/" + tag + path][method] = spec["paths"][path][method]
            log.debug("processed " + tag + path + " " + method)
    # replace paths object
    spec["paths"] = paths

    # save updated spec
    with open(args.output, "w") as write_file:
        json.dump(spec, write_file, indent=2)

    log.info("Wrote update OpenAPI docuement to " + args.output)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", help="Verbose (debug) logging", action="store_const", const=logging.DEBUG,
                       dest="loglevel")
    group.add_argument("-q", "--quiet", help="Silent mode, only log warnings", action="store_const",
                       const=logging.WARN, dest="loglevel")
    parser.add_argument("-f", "--file", help="OpenAPI document (defaults to swagger.json)",
                        metavar="FILENAME", default="swagger.json")
    parser.add_argument("-o", "--output", help="Output file",
                        metavar="FILENAME", required=True)
    parser.add_argument("-H", "--hostname", help="Identity Apps hostname (e.g. identityapps.example.com)",
                        metavar="HOSTNAME")
    parser.add_argument(
        "-p", "--port", help="Identity Apps port", metavar="PORT")
    parser.add_argument("-i", "--issuer", help="OAuth2 issuer (e.g. https://osp.example.com:8543/osp/a/idm/auth/oauth2)", metavar="URL"
                        )
    args = parser.parse_args()
    main(args)
