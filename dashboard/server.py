"""
Servidor web local para el dashboard de presencia.
Accesible desde cualquier dispositivo en la red local.

Uso:
  python dashboard/server.py
  python dashboard/server.py 8080  (puerto custom)

Acceder desde:
  - Este PC: http://localhost:8050
  - Red local: http://<tu-ip>:8050
"""
import os
import sys
import socket
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8050
DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def log_message(self, format, *args):
        # Log limpio
        print(f"  {self.address_string()} - {args[0]}")


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "?"


if __name__ == "__main__":
    local_ip = get_local_ip()
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"\n  Dashboard de Presencia")
    print(f"  ----------------------")
    print(f"  Local:    http://localhost:{PORT}/presencia.html")
    print(f"  Red:      http://{local_ip}:{PORT}/presencia.html")
    print(f"  Ctrl+C para detener\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Servidor detenido.")
