from http.server import BaseHTTPRequestHandler, HTTPServer
class StoreHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/dq-monitor/prometheus':
            with open('/APP/scripts/tracing.json') as fh:
                self.send_response(200)
                self.send_header('Content-type', 'text/json')
                self.end_headers()
                self.wfile.write(fh.read().encode())
server = HTTPServer(('', 8000), StoreHandler)
server.serve_forever()
