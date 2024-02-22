# eDirAPI - eDirectory REST gateway

## non-OSP mode

```sh
EDIRAPI_ORIGIN="https://identityconsole.example.com:9000"
TREE="idm48_tree" # must be lowercase
USER_DN="cn=admin,ou=sa,o=system"
USER_PASSWORD="<secert>"
LDAP_SERVER="edirectory.example.com"

# Login and save RSESSION cookie
curl --cookie-jar cookies.txt --location "$EDIRAPI_ORIGIN/eDirAPI/v1/session" --header "Origin: $EDIRAPI_ORIGIN" --header 'Content-Type: application/json' --data "{\"dn\":\"$USER_DN\",\"password\":\"$USER_PASSWORD\",\"ldapserver\":\"$LDAP_SERVER\"}"

# Get X-CSRF-Token and strip of quotes
X_CSRF_Token=$(curl --silent --cookie cookies.txt --location "$EDIRAPI_ORIGIN/eDirAPI/v1/$TREE/getanticsrftoken" | xargs)

# Request data
curl --cookie cookies.txt --location "$EDIRAPI_ORIGIN/eDirAPI/v1/$TREE/$USER_DN" --header "X-CSRF-Token: $X_CSRF_Token"
```
