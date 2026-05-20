"""Servidor HTTP minimal para test de conectividad."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = (
            f"<h1>OK</h1><p>Servidor accesible desde {self.client_address[0]}</p>"
            f"<p>Hora servidor: {datetime.now().isoformat()}</p>"
            f"<p>Ruta: {self.path}</p>"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *a):
        print(f"HIT|{self.client_address[0]}|{a[0]}", flush=True)


if __name__ == "__main__":
    srv = HTTPServer(("0.0.0.0", 8081), H)
    print(f"LISTEN|0.0.0.0:8081", flush=True)
    srv.serve_forever()
