# NetIQ Identity Applications REST API via curl and jq

In this article I'll demontrate how to use the curl and jq utilities in a bash command line to interact with Identity Applications via its REST API. The Identity Applications use the OAuth2 protocol for authentication and authorization. So before we can work with the Identity Apps, we first get an access token from OSP.

## Prerequisites

### Packages

- [curl](https://curl.haxx.se/)
- [jq](https://stedolan.github.io/jq/)

While curl is installed even if you select a minimal Linux distribution, jq packages are an add-on and available from extra modules:

- [RHEL/CentOS EPEL](https://fedoraproject.org/wiki/EPEL)
- [SUSE Package Hub](https://packagehub.suse.com/how-to-use/)

### OAuth client

In the OAuth terminology curl (and bash) are a [*client*](https://tools.ietf.org/html/rfc6749#section-2). We assume you are running on a secure server or workstation with restricted access to the client credentials. Thus we have a *confidential* client.

The easiest way to register a new OAuth client with OSP (our Authorization Server) is to edit the `ism-configuration.properties` file by hand and add the following properties:

```properties
com.example.playground.clientID = playground
com.example.playground.clientPass = secret
```

You can choose a `clientID` value and property name prefix (instead of `com.example.playground`) of your liking.

Instead of using a plain text client secret (`clientPass`) in the configuration file, you should generate an obfuscated value with:

```bash
java -jar /opt/netiq/idm/apps/tomcat/lib/obscurity-*jar "secret"
```

For obfuscated secrets, also add the `clientPass._attr_obscurity` property:

```properties
com.example.playground.clientID = playground
com.example.playground.clientPass._attr_obscurity = ENCRYPT
com.example.playground.clientPass = RUV4kYdFttA3C4hm5eltow==:vrWF02aufnZQeL9toAJyhQ==:GYeEL/1pPjrfxl1B8evASA==
```

Restart OSP.

### User

In addition to an OAuth client, you also need a user in the Identity Vault. We will be using the [Resource Owner Password Credentials Grant](https://tools.ietf.org/html/rfc6749#section-4.3), so you need the user's username and its password. To be able to call some of the endpoints shown here, the user must have administrative privileges.

### Endpoints

You need to know where OSP is deployed to get your OAuth endpoints. In a NetIQ Identity Manager quick start install, OSP is installed on the Identity Applications Tomcat running https on port 8543:

```bash
export OSP_ORIGIN="https://idmapps.example.com:8543"
```

With this you can retrieve the OAuth2/OpenID endpoints with:

```bash
export OAUTH2_ISSUER="${OSP_ORIGIN}/osp/a/idm/auth/oauth2"

curl -fsS "$OAUTH2_ISSUER/.well-known/openid-configuration" \
  | jq . \
  | tee openid-configuration.json

export AUTHORIZATION_ENDPOINT="$(jq -r .authorization_endpoint openid-configuration.json)"
export TOKEN_ENDPOINT="$(jq -r .token_endpoint openid-configuration.json)"
export USERINFO_ENDPOINT="$(jq -r .userinfo_endpoint openid-configuration.json)"
export REVOCATION_ENDPOINT="$(jq -r .revocation_endpoint openid-configuration.json)"
export INTROSPECTION_ENDPOINT="$(jq -r .introspection_endpoint openid-configuration.json)"
```

Note: To check if OSP is reachable (e.g. by a load balancer) use the URL `https://${OSP_ORIGIN}/osp/a/idm/auth/app/ping`.

## Authentication

### Setup environment

```bash
export CLIENT_ID="playground"
read -sp "password for client $CLIENT_ID: " CLIENT_SECRET && echo && export CLIENT_SECRET
```

```bash
export USERNAME="uaadmin"
read -sp "password for user $USERNAME: " PASSWORD && echo && export PASSWORD
```

### Login

Get access and refresh tokens and store them in `token.json`.

```bash
curl -fsS \
  --request POST \
  --url $TOKEN_ENDPOINT \
  --user "$CLIENT_ID:$CLIENT_SECRET" \
  --data "grant_type=password" \
  --data "username=$USERNAME" \
  --data "password=$PASSWORD" \
  -o token.json # login
```

**Note:** Don't forget to [logout](#logout) when done.

### Refresh access token

By deafult, OSP access tokens expire after 60 seconds. To get a new access token and store it in `access_token.json` (to avoid overwriting your refresh token) use:

```bash
curl -fsS \
  --request POST \
  --url $TOKEN_ENDPOINT \
  --user "$CLIENT_ID:$CLIENT_SECRET" \
  --data "grant_type=refresh_token" \
  --data "refresh_token=$(jq -r .refresh_token token.json)" \
  | jq '.exp = (now + .expires_in | floor) | .exp_date = (.exp | todate)' \
  > access_token.json # refresh access token
```

The 2nd jq command adds two expiration timestamp properties: `exp` (expiration date in seconds since the epoch) and `exp_date` (expiration date in ISO 8601 format):

```json
{
  "access_token": "...",
  "token_type": "Bearer",
  "expires_in": 60,
  "exp": 1598006322,
  "exp_date": "2020-08-21T10:38:42Z"
}
```

### Check token state (introspect)

Introspect access token:

```bash
curl -fsS \
  --request POST \
  --url $INTROSPECTION_ENDPOINT \
  --user "$CLIENT_ID:$CLIENT_SECRET" \
  --data "token=$(jq -r .access_token access_token.json)" \
  | jq . # check access token
```

Introspect refresh token and use jq to calculate its remaining life time in a human readable format:

```bash
curl -fsS \
  --request POST \
  --url $INTROSPECTION_ENDPOINT \
  --user "$CLIENT_ID:$CLIENT_SECRET" \
  --data "token=$(jq -r .refresh_token token.json)" \
  | jq 'if .exp
    then
      .exp_date = (.exp | todate) # expiration date in ISO 8601 format
      | .exp_duration = ((.exp - now ) | floor) # remaining lifetime in seconds
      | .remaining = "\(.exp_duration / 86400 | floor)d \(.exp_duration / 3600 % 24 | floor)h \(.exp_duration / 60 % 60 | floor)m \(.exp_duration % 60 | floor)s"
    else
      .exp_duration = 0
    end' # check refresh token
```

### Get user info

```bash
curl -fsS \
  --url "$USERINFO_ENDPOINT" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  --header "accept: application/json" \
  | jq .
```

## Manage OSP via REST endpoints

### Get meta data for tenant `idm`

Lists all configured OAuth clients.

```bash
curl -fsS \
  --url "$OSP_ORIGIN/osp/a/idm/auth/oauth2/metadata" \
  --header "accept: application/json" \
  | jq .
```

### Get a list of system-wide status indicators

```bash
curl -fsS \
  --url "$OSP_ORIGIN/osp/s/list" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  --header "accept: application/json" \
  | jq .
```

### Get system-wide logging level

```bash
curl -fsS \
  --url "$OSP_ORIGIN/osp/s/loglevel" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  --header "accept: application/json" \
  | jq .
```

### Set system-wide logging level

See [JavaDoc](https://docs.oracle.com/javase/8/docs/api/java/util/logging/Level.html) for a list of possible logging levels. To set level to `ALL` use:

```bash
curl -fsS \
  --request PUT \
  --url "$OSP_ORIGIN/osp/s/loglevel" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  --header "accept: application/json" \
  --header "content-type: application/json" \
  --data '{"level":"ALL"}' \
  | jq .
```

### Restart `idm` tenant

```bash
curl -fsS \
  --url "$OSP_ORIGIN/osp/s/restart/idm" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  --header "accept: application/json" \
  | jq .
```

## Interact with Identity Apps REST endpoints

### [Get version](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#/Access/resource_Access_getVersion_GET)

```bash
curl -fsS \
  --url "$IDMPROV_ORIGIN/IDMProv/rest/access/info/version" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq .
```

### [Get User Application driver status](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#/Admin/resource_Admin_getDriverStatusInfo_GET)

```bash
curl -fsS \
  --url "$IDMPROV_ORIGIN/IDMProv/rest/admin/driverstatus/info" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq .

```

### [Get log configuration](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#/Admin/resource_Admin_getLogConfigurations_GET)

```bash
curl -fsS \
  --url "$IDMPROV_ORIGIN/IDMProv/rest/admin/logging/list" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq .
```

### [Get Memory info](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#/Catalog/resource_Catalog_getSystemJVMMemoryInfo_GET)

```bash
curl -fsS \
  --url "$IDMPROV_ORIGIN/IDMProv/rest/access/statistics/memoryinfo" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq .
```

### [Get Thread info](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#/Catalog/resource_Catalog_getThreadInfo_GET)

```bash
curl -fsS \
  --url "$IDMPROV_ORIGIN/IDMProv/rest/access/statistics/threadinfo" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq .
```

### [CodeMap refresh for a single Entitlement](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#/Catalog/resource_Catalog_entitlementRefresh_POST)

```bash
curl -fsS \
  --url "$IDMPROV_ORIGIN/IDMProv/rest/catalog/codemaprefresh/entitlement" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  --data-raw '{
    "entitlements": [
        {
            "id": "cn=role,cn=rest-sentinel,cn=driverset1,o=system"
        }
    ]
}'  | jq . # codemap refresh
```

### [Flush cache](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#/Admin/resource_Admin_flushCacheByHolderID_DELETE)

```bash
curl -fsS \
  --request DELETE \
  --url "$IDMPROV_ORIGIN/IDMProv/rest/admin/cache/holder/items?cacheHolderID=All%20Cache" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq . # flush all caches
```

### Start a Workflow (PRD)

To start a workflow with the dedicated workflow engine in IDM 4.8, you need to use the `/IDMProv/rest/access/requests/permissions/v2` endoint.

To start a workflow `SampleWF` with one additional parameter named `sample1`, `POST` the following JSON :

```json
{
    "reqPermissions": [
        {
            "id": "cn=SampleWF,cn=RequestDefs,cn=AppConfig,cn=User Application Driver,cn=driverset1,o=system",
            "entityType": "PRD"
        }
    ],
    "data": [
        {
            "key": "reason",
            "value": [
                "test reason"
            ]
        },
        {
            "key": "recipient",
            "value": [
                "cn=uaadmin,ou=sa,o=data"
            ]
        },
        {
            "key": "sample",
            "value": [
                "sample"
            ]
        }
    ]
}
```

Multiple values for a parameter must be serialized as JSON array. he resulting string value must then be used as first array element of the `value` property:

```json
{
    "key": "userList",
    "value": [
        "[\"cn=David,o=data\",\"cn=Alen,o=data\"]"
    ]
}
```

As result you should get following response:

```json
{
    "success": true,
    "OperationNodes": [
        {
            "success": true,
            "succeeded": [
                {
                    "id": "cn=SampleWF,cn=RequestDefs,cn=AppConfig,cn=User Application Driver,cn=driverset1,o=system",
                    "requestId": "cd48b6808dfb4cc7a554c9b4aa32031a"
                }
            ],
            "userDn": "cn=uaadmin,ou=sa,o=data"
        }
    ]
}
```

Where `requestId` is unique identifier of started workflow instance.

#### Additional Information

If you need to get actual parameters of your non-JSON-form PRD, use the `/IDMProv/rest/access/permissions/item` endpoint and `POST` following JSON structure:

```json
{
  "id":"cn=SampleWF,cn=RequestDefs,cn=AppConfig,cn=User Application Driver,cn=driverset1,o=system",
  "entityType":"prd"
}
```

You you can find the parameters in the `dataItems` property of the response body:

```json
{
    "id": "cn=samplewf,cn=requestdefs,cn=appconfig,cn=user application driver,cn=driverset1,o=system",
    "dn": "cn=SampleWF,cn=RequestDefs,cn=AppConfig,cn=User Application Driver,cn=driverset1,o=system",
    "name": "SampleWF",
    "desc": "SampleWF",
    "entityType": "prd",
    "bulkRequestable": false,
    "categories": [
        "Custom Templates"
    ],
    "link": "/IDMProv/rest/access/permissions/item",
    "multiAssignable": true,
    "excluded": false,
    "requestForm": "PD9...",
    "dataItems": [
        {
            "name": "reason",
            "dataType": "string",
            "valueType": 2,
            "readOnly": false,
            "multiValued": "false",
            "valueSet": "false"
        },
        {
            "name": "recipient",
            "dataType": "dn",
            "valueType": 2,
            "readOnly": false,
            "multiValued": "false",
            "valueSet": "false"
        },
        {
            "name": "sample",
            "dataType": "string",
            "valueType": 2,
            "readOnly": false,
            "multiValued": "false",
            "valueSet": "false"
        }
    ],
    "edition": "rbpm.prd.1667987236179",
    "isNewForm": false,
    "isExpirationRequired": "false"
}
```

### More

See [REST API documentation](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#) for all available methods.

## Interact with Identity Reporting REST endpoints

### [purge database](https://www.netiq.com/documentation/identity-manager-48/report_setup/data/t42h1ese4ans.html)

```bash
curl -fsS \
  --request DELETE \
  --url "$RPT_ORIGIN/IDMDCS-CORE/rpt/collectors/data" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq . # purge reporting db
```

## Logout

Every login generates a new refresh token. These are stored in the `oidpInstanceData` attribute on the user object. This space is limited. You therefore must revoke your refresh token once you're done. Otherwise the user might fail to login again after some time.

```bash
curl -fsS \
  --request POST \
  --url $REVOCATION_ENDPOINT \
  --user "$CLIENT_ID:$CLIENT_SECRET" \
  --data "token_type_hint=refresh_token" \
  --data "token=$(jq -r .refresh_token token.json)" # logout
```
