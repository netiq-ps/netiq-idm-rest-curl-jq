
/*
 * if the access token expired and auto refresh has been set, use the refresh
 * token to create a new access token
 * if no refresh token is available, execute Resource Owner Password Credentials grant request
 * TODO: handle expired refresh token
 */

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
const tokenEndpoint = String(pm.environment.get('token_endpoint'))
const hasTokenEndpoint = tokenEndpoint.length > 0
if (!hasTokenEndpoint) {
    throw new Error('No token_endpoint. Check environment.')
}

// determine if we have all the client credentials needed in the environment
const hasClientId = String(pm.environment.get('client_id')).length > 0
if (!hasClientId) {
    throw new Error('No client_id. Check environment.')
}

const hasClientSecret = String(pm.environment.get('client_secret')).length > 0
if (!hasClientSecret) {
    throw new Error('No client_secret. Check environment.')
}

const hasRefreshToken = String(pm.environment.get('refresh_token')).length > 0
if (!hasRefreshToken) {
    // get refresh token
    const username = String(pm.environment.get('username'))
    const hasUsername = username.length > 0
    if (!hasUsername) {
        throw new Error('No username. Check environment.')
    }

    const password = String(pm.environment.get('password'))
    const haspassword = password.length > 0
    if (!hasUsername) {
        throw new Error('No password. Check environment.')
    }

    pm.sendRequest({
        url: tokenEndpoint,
        method: 'POST',
        headers: { 'Content-Type': 'Content-Type: application/x-www-form-urlencoded' },
        body: {
            mode: 'urlencoded',
            urlencoded: [
                { key: 'client_id', value: pm.environment.get('client_id'), disabled: false },
                { key: 'client_secret', value: pm.environment.get('client_secret'), disabled: false },
                { key: 'username', value: pm.environment.get('username'), disabled: false },
                { key: 'password', value: pm.environment.get('password'), disabled: false },
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
            // otherwise, fetch the new tokens and store it
            const data = response.json()

            // determine when this token is set to expire at
            const newExpiresAt = Date.now() + data.expires_in * 1000
            // store the new variables in the environment
            pm.environment.set('access_token', data.access_token)
            if ('refresh_token' in data) {
                pm.environment.set('refresh_token', data.refresh_token)
            }
            pm.environment.set('expires_at', newExpiresAt)

            console.info('Stored refresh token.')
        }
    })

    return
}

// send a new API request to refresh the access token
// console.log('refreshing token with ' + tokenEndpoint);
pm.sendRequest({
    url: tokenEndpoint,
    method: 'POST',
    headers: { 'Content-Type': 'Content-Type: application/x-www-form-urlencoded' },
    body: {
        mode: 'urlencoded',
        urlencoded: [
            { key: 'client_id', value: pm.environment.get('client_id'), disabled: false },
            { key: 'client_secret', value: pm.environment.get('client_secret'), disabled: false },
            { key: 'refresh_token', value: pm.environment.get('refresh_token'), disabled: false },
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
        throw new Error('Could not refresh the access token: ' + response.json().error)
    } else {
        // otherwise, fetch the new access token and store it
        const data = response.json()

        // determine when this token is set to expire at
        const newExpiresAt = Date.now() + data.expires_in * 1000
        // store the new variables in the environment
        pm.environment.set('access_token', data.access_token)
        if ('refresh_token' in data) {
            pm.environment.set('refresh_token', data.refresh_token)
        }
        pm.environment.set('expires_at', newExpiresAt)

        console.info('Refreshed access token.')
    }
})
