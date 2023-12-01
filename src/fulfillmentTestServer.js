//
// Sample of a simple nodejs server to test building HTTP/REST/SOAP fulfillment targets
//
// Use this to fine tune your request headers and body to debug any issues
// before running it against your production systems.
//
// Usage: node fulfillmentTestServer.js


const http = require('http')
const port = 3000
const { createHash } = require('node:crypto');

const defaultBaseIndex = 1; // 0 or 1 indexed
const totalCount = 5; // max number of results to return
const maxPageSize = totalCount; // number of retults to return if no page size is specified

var requestsTotalCount = 1; // counter of received HTTP requests

const requestHandler = (request, response) => {
  //  console.log(request.url)


  if (request.method == 'POST') {
    var requestBody = '';
  }

  request.on('data', function (data) {
    requestBody += data;
  });

  request.on('end', function () {
    const u = new URL(request.url, `http://${request.headers.host}`);
    console.log(new Date());
    console.log("Incoming request #" + requestsTotalCount + ": " + request.method + ' on ' + u);
    console.log("Request headers:  " + JSON.stringify(request.headers));
    if (requestBody) {
      console.log("Request body:    ", requestBody);
    }

    let contentType = request.headers['content-type'];
    let responseBody = '';
    if (contentType && contentType.includes('xml')) {
      response.setHeader('content-type', request.headers['content-type']);
      responseBody = buildSoapContent();
    } else {
      response.setHeader('content-type', 'application/json');
      responseBody = buildJsonContent(u, requestsTotalCount);
    }

    console.log("Response headers: " + JSON.stringify(response.getHeaders()));
    console.log('Response body:   ', responseBody);
    response.end(responseBody);

    console.log("");
    requestsTotalCount++;
  });
}

const server = http.createServer(requestHandler)

server.listen(port, (err) => {
  if (err) {
    return console.log('error starting server', err)
  }

  console.log(`server is listening on ${port}`)
})

var buildSoapContent = function () {
  var soap = '<?xml version="1.0" ?>\n';
  soap += '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">\n';
  soap += '	<soapenv:Body xmlns:m="http://www.myservice.com/incident">\n';
  soap += '		<m:insertResponse>\n';
  soap += '			<ticketNumber>' + requestsTotalCount + '</ticketNumber>\n';
  soap += '		</m:insertResponse>\n';
  soap += '	</soapenv:Body>\n';
  soap += '</soapenv:Envelope>';

  return soap;
}


var buildJsonContent = function (u, requestsTotalCount) {
  const baseIndex = u.searchParams.has('baseIndex') ? Number(u.searchParams.get('baseIndex')) : defaultBaseIndex;
  const startIndex = u.searchParams.has('startIndex') ? Number(u.searchParams.get('startIndex')) : baseIndex;
  const pageSize = u.searchParams.has('count') ? Number(u.searchParams.get('count')) : maxPageSize;

  const o = {};
  o.request = requestsTotalCount;
  o.baseIndex = baseIndex;
  o.startIndex = startIndex;
  o.pageSize = pageSize;
  o.totalCount = totalCount;

  o.results = [];
  for (var i = Math.max(baseIndex, startIndex); i < startIndex + pageSize && i < totalCount + baseIndex; i++) {
    const hash = createHash('sha256');
    hash.update(String(i));
    o.results.push({ 'data': hash.digest('hex'), 'id': i });
  }

  const body = JSON.stringify(o);
  return body;
}
