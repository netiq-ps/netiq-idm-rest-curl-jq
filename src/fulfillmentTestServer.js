//
// Sample of a simple nodejs server to test building HTTP/REST/SOAP fulfillment targets
//
// Use this to fine tune your request headers and body to debug any issues
// before running it against your production systems.
//
// Usage: node fulfillmentTestServer.js

 
const url = require('node:url');
const http = require('http')
const port = 3000
const { createHash } = require('node:crypto');


const requestHandler = (request, response) => {
//  console.log(request.url)


  if (request.method == 'POST') {
    var body = '';
  }

  request.on('data', function (data) {
    body += data;
  });

  request.on('end', function () {
    var u = new URL(request.url, `http://${request.headers.host}`);
    console.log(new Date());	  
    console.log("Incoming request #" + requestsTotalCount + ": " + request.method + ' on ' + request.url);
    //console.log(u);
    console.log("Request headers: " + JSON.stringify(request.headers));
    if (body) {
	    console.log("Request body:", body);
    }

    if (request.headers['content-type'] && request.headers['content-type'].indexOf('xml') > 0) {
      response.setHeader('content-type', request.headers['content-type']);
      response.end(buildSoapContent());
    } else {
       response.setHeader('content-type', 'application/json');
       response.end(buildJsonContent(u, 5, requestsTotalCount));
    }
    console.log("Response headers: " + JSON.stringify(response.getHeaders()));
    requestsTotalCount++;
    console.log("");
  });
}

const server = http.createServer(requestHandler)

server.listen(port, (err) => {
  if (err) {
    return console.log('error starting server', err)
  }

  console.log(`server is listening on ${port}`)
})

var buildSoapContent = function() {
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


var buildJsonContent = function(u, totalCount, requestsTotalCount) {
	const firstIndex = Number(u.searchParams.get('startIndex'));
	const pageSize = Number(u.searchParams.get('count'));
	const o = {};
	o.totalCount = 5;
	o.request = requestsTotalCount;
	o.firstIndex = firstIndex;
	o.pageSize = pageSize;

	o.results = [];
		const hash = createHash('sha256');
		hash.update(String(i));
		o.results.push({'data':hash.digest('hex'),'id':i});
	}

	const body = JSON.stringify(o);
	console.log('Response body:  ', body);
	return body;
}
