#!/usr/bin/env python3
"""Fix issues in the NetIQ Identity Applications OpenAPI document.

This script fixes issues in swagger.json. It can also add security and server settings to make the document easily consumable by API tools such as Postman or Swagger.
"""

"""
MIT License

Copyright (c) 2021 Micro Focus

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


from argparse import ArgumentParser
import json
import logging
import requests
import yaml
log = logging.getLogger(__name__)
FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"


# Sibling values alongside $refs are ignored. To add properties to a $ref, wrap the $ref into allOf, or move the extra properties into the referenced definition (if applicable).
# Recursivly enumerate JSON (dict) structure to find references and remove members other than "$ref"
def removeRefSiblings(node):
    if isinstance(node, dict):
        if "$ref" in node:
            for key in list(node):
                if key != "$ref":
                    del node[key]
        else:
            for key, value in node.items():
                if isinstance(value, dict):
                    removeRefSiblings(value)
                elif isinstance(value, list) or isinstance(value, tuple):
                    for v in value:
                        removeRefSiblings(v)


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

    # "attribute paths.'/access/data/migration/workflow'(post).[body].type is unexpected"
    # If type is "file", the parameter MUST be in "formData". https://swagger.io/specification/v2/#parameterObject
    # Remove extra parameter alternative with in=body
    spec["paths"]["/data/migration/workflow"]["post"]["parameters"].pop()

    # fix duplicate operation ids
    spec["paths"][r"/codeMap/{id}/values"]["get"]["operationId"] = "resource_Access_fetchCodeMapValues_GET"
    spec["paths"]["/requests/historylist"]["get"]["operationId"] = "resource_Access_getLoggedInUserPermissionRequestHistoryList_GET"
    spec["paths"]["/featuredItems/categories"]["delete"]["operationId"] = "resource_Access_deleteFeaturedItemsCategories_DELETE"
    spec["paths"]["/featuredItems/categories"]["post"]["operationId"] = "resource_Access_addFeaturedItemsCategories_POST"
    spec["paths"]["/featuredItems/categories"]["put"]["operationId"] = "resource_Access_updateFeaturedItemsCategories_PUT"
    spec["paths"]["/featuredItems"]["put"]["operationId"] = "resource_Access_updateFeaturedItems_PUT"
    spec["paths"]["/featuredItems"]["post"]["operationId"] = "resource_Access_addFeaturedItems_POST"
    spec["paths"]["/featuredItems"]["delete"]["operationId"] = "resource_Access_deleteFeaturedItems_DELETE"
    spec["paths"]["/workflow"]["post"]["operationId"] = "resource_Access_validateCreatePRD_POST"
    spec["paths"]["/roleCategories"]["get"]["operationId"] = "role_Catalog_searchCategories_GET"
    spec["paths"]["/roles/role/assignments/assign"]["post"]["operationId"] = "role_Catalog_assignRoleAssignments_POST"

    # attribute paths.'/access/config/helpdesk'(post).[body].description is unexpected
    # remove sibling values alongside $refs
    removeRefSiblings(spec)

    # The original base path is set to /IDMProv/rest/access. This is wrong for admin, catalog, and monitoring endpoints.
    # Remove 3rd element from basePath and add it to individual paths instead.
    spec["basePath"] = "/IDMProv/rest"
    paths = {}
    for path in spec["paths"]:
        for method in spec["paths"][path]:
            # fix tag (and path) for health statistics monitoring endpoints
            # https://www.netiq.com/documentation/identity-manager-48/setup_windows/data/b1biz3l8.html#t41u0zsov9gr
            if (path.startswith("/statistics")):
                spec["paths"][path][method]["tags"][0] = "Monitoring"

            # Determine correct 3rd path element from endpoint's tag and prepend it to existing path
            tag = (spec["paths"][path][method]["tags"][0]).lower()
            # create node if necessary
            if (not ("/" + tag + path) in paths):
                paths["/" + tag + path] = {}
            # copy over method definition
            if (method in paths["/" + tag + path]):
                log.error("/" + tag + path + "(" + method + ") already exists")
            else:
                paths["/" + tag + path][method] = spec["paths"][path][method]
            log.debug("processed " + tag + path + " " + method)
    # replace paths object
    spec["paths"] = paths

    log.info("Saving")

    # save updated spec
    if args.output.endswith("yaml"):
        with open(args.output, "w") as yaml_file:
            yaml.dump(spec, yaml_file, sort_keys=True)
    else:
        with open(args.output, "w") as json_file:
            json.dump(spec, json_file, indent=2, sort_keys=True)

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
        "-p", "--port", help="Identity Apps HTTPS port", metavar="PORT")
    parser.add_argument("-i", "--issuer", help="OAuth2 issuer (e.g. https://osp.example.com:8543/osp/a/idm/auth/oauth2)", metavar="URL"
                        )
    args = parser.parse_args()
    main(args)
