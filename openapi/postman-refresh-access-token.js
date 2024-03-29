/*
 * Postman pre-request script to get access tokens using the Resource Owner Password Credentials grant.
 * Automatically refreshes acces token if expired.
 * 
 * Put the code into Collection -> Pre-request Script 
 * Set Collection -> Authorization -> Current Token -> Access Token to {{access_token}}
 * TODO: programatically handle expired refresh token
 */

// skip if trying to retrieve .well-known meta-data
if (pm.info.requestName == 'openid-configuration') {
    return
}

// determine if the user has auto-refresh enabled
const autoRefresh = String(pm.environment.get('enable_auto_refresh_access_token')) === 'true'
if (!autoRefresh) {
    console.warn("autoRefresh is disabled.")
    return
}

// determine if the Access Token has expired
const expiresAt = pm.environment.get('expires_at')
const accessTokenTTL = Number(expiresAt) - Date.now()
if (accessTokenTTL > 0) {
    console.log("Access token is still valid for " + (Number(expiresAt) - Date.now()) + " ms. Skipping refresh.")
    return
}

// determine if Token Endpoint is set in the environment
const tokenEndpoint = pm.environment.get('token_endpoint')
if (!tokenEndpoint) {
    throw new Error('No token_endpoint. Check environment.')
}

// determine if we have all the client credentials needed in the environment
const clientID = pm.environment.get('client_id')
if (!clientID) {
    throw new Error('No client_id. Check environment.')
}

const refreshToken = pm.environment.get('refresh_token')
if (!refreshToken) {
    // get refresh token using Resource Owner Password Credentials grant

    const clientSecret = pm.environment.get('client_secret')
    if (!clientSecret) {
        throw new Error('No client_secret. Check environment.')
    }
    
    const username = String(pm.environment.get('username'))
    if (!username) {
        throw new Error('No username. Check environment.')
    }

    const password = String(pm.environment.get('password'))
    if (!password) {
        throw new Error('No password. Check environment.')
    }

    pm.sendRequest({
        url: tokenEndpoint,
        method: 'POST',
        headers: { 'Content-Type': 'Content-Type: application/x-www-form-urlencoded' },
        body: {
            mode: 'urlencoded',
            urlencoded: [
                { key: 'client_id', value: clientID, disabled: false },
                { key: 'client_secret', value: clientSecret, disabled: false },
                { key: 'username', value: username, disabled: false },
                { key: 'password', value: password, disabled: false },
                { key: 'grant_type', value: 'password', disabled: false }
            ]
        }
    }, function (error, response) {
        if (error) {
            // if an error occured, log the error and raise a message to the user.
            console.error(error)
            throw new Error('Could not get the refresh token: ' + JSON.stringify(error))
        } else if (response.json().error) {
            console.error(response.json())
            throw new Error('Could not get the refresh token: ' + response.json().error)
        } else {
            // otherwise, update tokens
            const data = response.json()

            // store the new tokens in the environment
            pm.environment.set('access_token', data.access_token)
            if ('refresh_token' in data) {
                pm.environment.set('refresh_token', data.refresh_token)
            }

            // determine when access token is set to expire at
            const newExpiresAt = Date.now() + data.expires_in * 1000
            pm.environment.set('expires_at', newExpiresAt)

            console.log('Stored refresh token.')
        }
    })

    return
}

// refresh access token
// console.log('refreshing token with ' + tokenEndpoint);
pm.sendRequest({
    url: tokenEndpoint,
    method: 'POST',
    headers: { 'Content-Type': 'Content-Type: application/x-www-form-urlencoded' },
    body: {
        mode: 'urlencoded',
        urlencoded: [
            { key: 'client_id', value: clientID, disabled: false },
            { key: 'client_secret', value: clientSecret, disabled: false },
            { key: 'refresh_token', value: refreshToken, disabled: false },
            { key: 'grant_type', value: 'refresh_token', disabled: false }
        ]
    }
}, function (error, response) {
    if (error) {
        // if an error occured, log the error and raise a message to the user.
        console.error(error)
        throw new Error('Could not refresh the access token: ' + JSON.stringify(error))
    } else if (response.json().error) {
        console.error(response.json())
        if (response.json().sub_error == "exptoken") {
            pm.environment.unset("refresh_token")
            throw new Error('Deleted expired refresh_token from environment. Please retry!')
        } else {
            throw new Error('Could not refresh the access token: ' + response.json().error_description + ' Delete refresh_token from environment if it is expired.')
        }
    } else {
        // otherwise, update tokens
        const data = response.json()

        // store the new tokens in the environment
        pm.environment.set('access_token', data.access_token)
        if ('refresh_token' in data) {
            pm.environment.set('refresh_token', data.refresh_token)
            console.log('Stored refresh token.')
        }

        // determine when access token is set to expire at
        const newExpiresAt = Date.now() + data.expires_in * 1000
        pm.environment.set('expires_at', newExpiresAt)

        console.log('Refreshed access token.')
    }
})
