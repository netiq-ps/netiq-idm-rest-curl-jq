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

The easiest way to register a new OAuth client with OSP (our Authorization Server) is to edit the `ism-configuration.properties` file by hand and add the following three properties:

```properties
com.example.playground.clientID = playground
com.example.playground.clientPass = secret
```

You can choose a `clientID` value and property name prefix (instead of `com.example.playground`) of your liking.

Instead of using a plain text client password in the configuration file, you should generate an obfuscated client secret (`clientPass`) value with:

```bash
java -jar /opt/netiq/idm/apps/tomcat/lib/obscurity-*jar "secret"
```

Restart OSP.

### User

In addition to an OAuth client, you also need a user in the Identity Vault. We will be using the [Resource Owner Password Credentials Grant](https://tools.ietf.org/html/rfc6749#section-4.3), so you need the user's username and its password. To be able to call some of the endpoints shown here, the user must have administrative privileges.

### Endpoints

You need to know your OAuth issuer URL. For OSP installed with NetIQ Identity Manager this defaults to `https://idmapps.example.com:8543/osp/a/idm/auth/oauth2`. From this you can retrieve the OAuth2/OpenID endpoints with:

```bash
export BASE_URL="https://idmapps.example.com:8543"
export OAUTH2_ISSUER="${BASE_URL}/osp/a/idm/auth/oauth2"

curl -fsS "$OAUTH2_ISSUER/.well-known/openid-configuration" \
  | jq . \
  | tee openid-configuration.json

export AUTHORIZATION_ENDPOINT="$(jq -r .authorization_endpoint openid-configuration.json)"
export TOKEN_ENDPOINT="$(jq -r .token_endpoint openid-configuration.json)"
export USERINFO_ENDPOINT="$(jq -r .userinfo_endpoint openid-configuration.json)"
export REVOCATION_ENDPOINT="$(jq -r .revocation_endpoint openid-configuration.json)"
export INTROSPECTION_ENDPOINT="$(jq -r .introspection_endpoint openid-configuration.json)"
```

## Authentication

### Setup environment

```bash
export CLIENT_ID="playground"
read -sp "password for client $CLIENT_ID: " CLIENT_PASSWORD && echo && export CLIENT_PASSWORD
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
  --user "$CLIENT_ID:$CLIENT_PASSWORD" \
  --data "grant_type=password" \
  --data "username=$USERNAME" \
  --data "password=$PASSWORD" \
  -o token.json # login
```

### Refresh access token

By deafult, OSP access tokens expire after 60 seconds. To get a new access token and store it in `access_token.json` (to avoid overwriting your refresh token) use:

```bash
curl -fsS \
  --request POST \
  --url $TOKEN_ENDPOINT \
  --user "$CLIENT_ID:$CLIENT_PASSWORD" \
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
  --user "$CLIENT_ID:$CLIENT_PASSWORD" \
  --data "token=$(jq -r .access_token access_token.json)" \
  | jq . # check access token
```

Introspect refresh token and use jq to calculate its remaining life time in a human readable format:

```bash
curl -fsS \
  --request POST \
  --url $INTROSPECTION_ENDPOINT \
  --user "$CLIENT_ID:$CLIENT_PASSWORD" \
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
  --url "$BASE_URL/osp/a/idm/auth/oauth2/metadata" \
  --header "accept: application/json" \
  | jq .
```

### Get a list of system-wide status indicators

```bash
curl -fsS \
  --url "$BASE_URL/osp/s/list" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  --header "accept: application/json" \
  | jq .
```

### Get system-wide logging level

```bash
curl -fsS \
  --url "$BASE_URL/osp/s/loglevel" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  --header "accept: application/json" \
  | jq .
```

### Set system-wide logging level

See [JavaDoc](https://docs.oracle.com/javase/8/docs/api/java/util/logging/Level.html) for a list of possible logging levels. To set level to `ALL` use:

```bash
curl -fsS \
  --request PUT \
  --url "$BASE_URL/osp/s/loglevel" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  --header "accept: application/json" \
  --header "content-type: application/json" \
  --data '{"level":"ALL"}' \
  | jq .
```

### Restart `idm` tenant

```bash
curl -fsS \
  --url "$BASE_URL/osp/s/restart/idm" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  --header "accept: application/json" \
  | jq .
```

## Interact with Identity Apps REST endpoints

### [Get version](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#/Access/resource_Access_getVersion_GET)

```bash
curl -fsS \
  --url "$BASE_URL/IDMProv/rest/access/info/version" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq .
```

### [Get User Application driver status](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#/Admin/resource_Admin_getDriverStatusInfo_GET)

```bash
curl -fsS \
  --url "$BASE_URL/IDMProv/rest/admin/driverstatus/info" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq .

```

### [Get log configuration](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#/Admin/resource_Admin_getLogConfigurations_GET)

```bash
curl -fsS \
  --url "$BASE_URL/IDMProv/rest/admin/logging/list" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq .
```

### [Get Memory info](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#/Catalog/resource_Catalog_getSystemJVMMemoryInfo_GET)

```bash
curl -fsS \
  --url "$BASE_URL/IDMProv/rest/access/statistics/memoryinfo" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq .
```

### [Get Thread info](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#/Catalog/resource_Catalog_getThreadInfo_GET)

```bash
curl -fsS \
  --url "$BASE_URL/IDMProv/rest/access/statistics/threadinfo" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq .
```

### [Flush cache](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#/Admin/resource_Admin_flushCacheByHolderID_DELETE)

```bash
curl -fsS \
  --request DELETE \
  --url "$BASE_URL/IDMProv/rest/admin/cache/holder/items?cacheHolderID=All%20Cache" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq . # flush all caches
```

### Start PRD

Use following minimal JSON structure to start workflow assuming that your workflow is named `testWF2` and it has two parameters named `sample1` and `sample2`:

```json
{
    "id":"cn=testWF2,cn=RequestDefs,cn=AppConfig,cn=User Application Driver,cn=driverset1,o=system",
    "entityType":"prd",
    "effDate": "",
    "expDate": "",
    "reason":"Just reason",
    "dataItems": [
        {
            "name": "sample1",
            "dataType": "string",
            "valueType": 2,
            "readOnly": false,
            "multiValued": "false",
            "values": [
                "something1"
            ]
        },
        {
            "name": "sample2",
            "dataType": "string",
            "valueType": 2,
            "readOnly": false,
            "multiValued": "false",
            "values": [
                "something2"
            ]
        },
        {
            "name": "recipient",
            "dataType": "dn",
            "valueType": 2,
            "readOnly": true,
            "multiValued": "false",
            "values": [
                "cn=uaadmin,ou=sa,o=data"
            ]
        }
    ]
}
```

As result you should get following response:

```json
{
    "success": true,
    "succeeded": [
        {
            "id": "cn=testWF2,cn=RequestDefs,cn=AppConfig,cn=User Application Driver,cn=driverset1,o=system",
            "instanceId": "22fb8d77a537413e9a7387f1700ba2c9"
        }
    ]
}
```

Where instanceID is unique identifier of started workflow (easy to find in catalina.out).

#### Additional Information

If you need to check actual parameters of your PRD use `/IDMProv/rest/access/permissions/item` endpoint and sent following JSON structure:

```json
{
  "id":"cn=testWF2,cn=RequestDefs,cn=AppConfig,cn=User Application Driver,cn=driverset1,o=system",
  "entityType":"prd"
}
```

You will get full details about your workflow with parameters required to send - just copy&paste them to JSON for `/IDMProv/rest/access/requests/permissions/item` request, add some values like in sample above and you are done.

Remark: all endpoints mentioned above (/IDMProv/rest/access/requests/permissions/item, /IDMProv/rest/access/permissions/item, /IDMProv/rest/access/requests/permissions) are intended for the `POST` method.

### More

See [REST API documentation](https://www.netiq.com/documentation/identity-manager-developer/rest-api-documentation/idmappsdoc/#) for all available methods.

## Interact with Identity Reporting REST endpoints

### [purge database](https://www.netiq.com/documentation/identity-manager-48/report_setup/data/t42h1ese4ans.html)

```bash
curl -fsS \
  --request DELETE \
  --url "$BASE_URL/IDMDCS-CORE/rpt/collectors/data" \
  --header "authorization: $(jq -r '.token_type + " " + .access_token' access_token.json)" \
  | jq . # purge reporting db
```

## Logout

Every login generates a new refresh token. These are stored in the `oidpInstanceData` attribute on the user object. This space is limited. You therefore must revoke your refresh token once you're done. Otherwise the user might fail to login again after some time.

```bash
curl -fsS \
  --request POST \
  --url $REVOCATION_ENDPOINT \
  --user "$CLIENT_ID:$CLIENT_PASSWORD" \
  --data "token_type_hint=refresh_token" \
  --data "token=$(jq -r .refresh_token token.json)" # logout
```
