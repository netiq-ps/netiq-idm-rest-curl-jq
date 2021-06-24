#!/bin/bash
export OSP_BASE_URL="https://idmapps.example.com:8543"
export IDMPROV_BASE_URL=$OSP_BASE_URL
export RPT_BASE_URL=$OSP_BASE_URL

export CLIENT_ID="playground"
read -sp "password for client $CLIENT_ID: " CLIENT_SECRET && echo && export CLIENT_SECRET
export USERNAME="uaadmin"
read -sp "password for user $USERNAME: " PASSWORD && echo && export PASSWORD

export OAUTH2_ISSUER="${OSP_BASE_URL}/osp/a/idm/auth/oauth2"

curl -fsS "$OAUTH2_ISSUER/.well-known/openid-configuration" -o openid-configuration.json
#jq . openid-configuration.json

export AUTHORIZATION_ENDPOINT="$(jq -r .authorization_endpoint openid-configuration.json)"
export TOKEN_ENDPOINT="$(jq -r .token_endpoint openid-configuration.json)"
export USERINFO_ENDPOINT="$(jq -r .userinfo_endpoint openid-configuration.json)"
export REVOCATION_ENDPOINT="$(jq -r .revocation_endpoint openid-configuration.json)"
export INTROSPECTION_ENDPOINT="$(jq -r .introspection_endpoint openid-configuration.json)"
