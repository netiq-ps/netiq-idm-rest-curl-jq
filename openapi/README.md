# OpenAPI

## [IdentityApps (aka UserApp or IDMProv)](idmprov)

- OpenAPI spec
- Python script to fix errors in OpenAPI spec
- Postman collection and sample environment

## [OSP](osp)

- Postman collection and sample environment

## Postman

To enable automatic token refresh after importing a [Postman](https://postman.com) collection and environment, edit the collection and set Authorization -> Current Token -> Access Token to `{{access_token}}`:

![Set Access Token field to environment variable](postman-collection-current-token.png)

## Swagger UI
(
To run Swagger UI locally and automatically load a predefined OpenAPI document with validation disabled (validation calls a remote service) run a [swagger-ui](https://hub.docker.com/r/swaggerapi/swagger-ui) container as follows:

```bash
run -it -p 8080:8080 -v netiq-idm-rest-curl-jq/openapi/idmprov/swagger.json:/usr/share/nginx/html/swagger.json --name swagger-ui -e SWAGGER_JSON=/usr/share/nginx/html/swagger.json -e VALIDATOR_URL=none  swaggerapi/swagger-ui:v3.51.1
```

