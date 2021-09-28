#!/bin/bash

# store token files in user's home directory
# file mode is set to 600, so files are only accessible by the user
ACCESS_TOKEN_FILE="$HOME/.access_token.json"
REFRESH_TOKEN_FILE="$HOME/.refresh_token.json"

osp_login () {
    touch "$REFRESH_TOKEN_FILE"
    chmod 600 "$REFRESH_TOKEN_FILE"
    curl -fsS \
        --request POST \
        --url $TOKEN_ENDPOINT \
        --output "$REFRESH_TOKEN_FILE" \
        --user "$CLIENT_ID:$CLIENT_SECRET" \
        --data "grant_type=password" \
        --data "username=$USERNAME" \
        --data "password=$PASSWORD" #\
#        --data "response_type=code id_token token" \
#        --data "scope=openid"
    if [[ $? == 0 ]]; then
        # ensure file exists with correct permissions
        touch "$ACCESS_TOKEN_FILE"
        chmod 600 "$ACCESS_TOKEN_FILE"
        # extract access token to its own file and store absolute expiration
        jq '{access_token:.access_token, token_type:.token_type, expires_in:.expires_in, exp:(now + .expires_in | floor)}' "$REFRESH_TOKEN_FILE" > "$ACCESS_TOKEN_FILE"

        # show refresh token info
        osp_check_refresh_token
    fi
}

# refresh access token is its remaining lifetime is less than 2s.
osp_refresh_access_token () {
    NEED_REFRESH="true"
    if [[ -s "$ACCESS_TOKEN_FILE" ]]; then # True if file exists and has a size greater than zero.
        NEED_REFRESH=$(jq '.exp < now - 2' "$ACCESS_TOKEN_FILE")
    else
        # ensure file exists with correct permissions
        touch "$ACCESS_TOKEN_FILE"
        chmod 600 "$ACCESS_TOKEN_FILE"
    fi
    if [[ "$NEED_REFRESH" == "true" ]]; then
        ACCESS_TOKEN=$(curl -fsS \
            --request POST \
            --url $TOKEN_ENDPOINT \
            --user "$CLIENT_ID:$CLIENT_SECRET" \
            --data "grant_type=refresh_token" \
            --data "refresh_token=$(jq -r .refresh_token $REFRESH_TOKEN_FILE)")
        res=$?
        if [[ $res == 0 ]]; then
            printf "%s" "$ACCESS_TOKEN" | jq '. | .exp=(now + .expires_in | floor)' > "$ACCESS_TOKEN_FILE"
            echo "refreshed access token" >&2
        else
            echo "error refreshing access token"
            return $res
        fi
    else
        echo "access token is still valid" >&2
    fi
}

osp_check_access_token () {
    curl -fsS \
    --request POST \
    --url $INTROSPECTION_ENDPOINT \
    --user "$CLIENT_ID:$CLIENT_SECRET" \
    --data "token=$(jq -r .access_token "$ACCESS_TOKEN_FILE")" \
    | jq 'if .exp
        then
            (.exp - now) as $remaining_lifetime_seconds
            | .exp_date = (.exp | todate) # expiration date in ISO 8601 format
            | .remaining_lifetime_seconds = $remaining_lifetime_seconds
            | .remaining_lifetime = "\($remaining_lifetime_seconds / 86400 | floor)d \($remaining_lifetime_seconds / 3600 % 24 | floor)h \($remaining_lifetime_seconds / 60 % 60 | floor)m \($remaining_lifetime_seconds % 60 | floor)s"
        else
            .
        end'
}

osp_check_refresh_token () {
    curl -fsS \
    --request POST \
    --url $INTROSPECTION_ENDPOINT \
    --user "$CLIENT_ID:$CLIENT_SECRET" \
    --data "token=$(jq -r .refresh_token $REFRESH_TOKEN_FILE)" \
    | jq 'if .exp
        then
            (.exp - now) as $remaining_lifetime_seconds
            | .exp_date = (.exp | todate) # expiration date in ISO 8601 format
            | .remaining_lifetime_seconds = $remaining_lifetime_seconds
            | .remaining_lifetime = "\($remaining_lifetime_seconds / 86400 | floor)d \($remaining_lifetime_seconds / 3600 % 24 | floor)h \($remaining_lifetime_seconds / 60 % 60 | floor)m \($remaining_lifetime_seconds % 60 | floor)s"
        else
            .
        end'
}

osp_user_info () {
    osp_refresh_access_token
    res=$?
    if [[ $res == 0 ]]; then
        curl -fsS \
        --url "$USERINFO_ENDPOINT" \
        --header "authorization: $(jq -r '.token_type + " " + .access_token' $ACCESS_TOKEN_FILE)" \
        --header "accept: application/json" \
        | jq .
    fi
}

# logout by revoking refresh token
osp_logout () {
    if [[ -s "$REFRESH_TOKEN_FILE" ]]; then
        curl -fsS \
        --request POST \
        --url $REVOCATION_ENDPOINT \
        --user "$CLIENT_ID:$CLIENT_SECRET" \
        --data "token_type_hint=refresh_token" \
        --data "token=$(jq -r .refresh_token $REFRESH_TOKEN_FILE)"
        rm "$ACCESS_TOKEN_FILE" "$REFRESH_TOKEN_FILE"
    fi
}


# osp system endpoints

osp_request () {
    osp_refresh_access_token
    curl -fsS \
    --request "$1" \
    --url "$2" \
    --header "authorization: $(jq -r '.token_type + " " + .access_token' $ACCESS_TOKEN_FILE)" \
    --header "accept: application/json" \
    --header "content-type: application/json" \
    --data "$3" \
    | jq .
}

osp_status () {
    osp_request "GET" "$OSP_BASE_URL/osp/s/list"
}

osp_health () {
    osp_request "GET" "$OSP_BASE_URL/osp/s/health"
}

osp_clients () {
    osp_request "GET" "$OSP_BASE_URL/osp/a/idm/auth/oauth2/clientRegistration"
}

osp_cluster_nodes () {
    osp_request "GET" "$OSP_BASE_URL/osp/s/cluster/nodes"
}

osp_get_loglevel () {
    osp_request "GET" "$OSP_BASE_URL/osp/s/loglevel"
}

osp_set_loglevel () {
    osp_request "PUT" "$OSP_BASE_URL/osp/s/loglevel" '{"level":"'$1'"}'
}

# Set framework logging configuration to the most verbose level.
osp_verbose_logging () {
    osp_request "GET" "$OSP_BASE_URL/osp/s/verboseLogging"
}

# Revert framework logging level to the level specified by configuration.
osp_reset_loglevel () {
    osp_request "GET" "$OSP_BASE_URL/osp/s/revertLogging"
}

# Restart system.
osp_restart () {
    osp_request "GET" "$OSP_BASE_URL/osp/s/restart"
}

# Cause the container (tomcat or jetty) to reload the OSP context.
osp_reload () {
    osp_request "GET" "$OSP_BASE_URL/osp/s/reload"
}


# idenity application endpoints

idmprov_request () {
    osp_refresh_access_token
    curl -fsS \
    --request "$1" \
    --url "$2" \
    --header "authorization: $(jq -r '.token_type + " " + .access_token' $ACCESS_TOKEN_FILE)" \
    --header "accept: application/json" \
    | jq .
}

idmprov_version () {
    idmprov_request "GET" "$IDMPROV_BASE_URL/IDMProv/rest/access/info/version"
}

idmprov_driverstatus () {
    idmprov_request "GET" "$IDMPROV_BASE_URL/IDMProv/rest/admin/driverstatus/info"
}

idmprov_cacheinfo () {
    idmprov_request "GET" "$IDMPROV_BASE_URL/IDMProv/rest/catalog/statistics/cacheinfo"
}

idmprov_flush_cache () {
    idmprov_request "DELETE" "$IDMPROV_BASE_URL/IDMProv/rest/admin/cache/holder/items?cacheHolderID=All%20Cache"
}



idmprov_user_rights () {
    idmprov_request "GET" "$IDMPROV_BASE_URL/IDMProv/rest/access/info/user/rights"
}

idmprov_roles () {
    idmprov_request "GET" "$IDMPROV_BASE_URL/IDMProv/rest/catalog/roles/listV2?$1"
}

idmprov_users () {
    idmprov_request "GET" "$IDMPROV_BASE_URL/IDMProv/rest/access/users/list?$1"
}
