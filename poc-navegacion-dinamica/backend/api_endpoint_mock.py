import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from manifest_generator import generate_layout_manifest


class ManifestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Endpoint: /get_layout_manifest?role=owner
        if self.path.startswith("/get_layout_manifest"):
            # Extraer el rol de la query string
            import urllib.parse as urlparse

            query = urlparse.urlparse(self.path).query
            params = urlparse.parse_qs(query)

            role = params.get("role", ["employee"])[0]  # Default: employee

            print(f"Request for manifest - Role: {role}")

            manifest = generate_layout_manifest(role)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")  # Permitir CORS para el PoC
            self.end_headers()

            self.wfile.write(json.dumps(manifest, indent=2).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")


def run():
    server_address = ("", 8080)
    httpd = HTTPServer(server_address, ManifestHandler)
    print("🚀 PoC Backend corriendo en http://localhost:8080")
    print("Prueba los roles:")
    print(" - http://localhost:8080/get_layout_manifest?role=superadmin")
    print(" - http://localhost:8080/get_layout_manifest?role=owner")
    print(" - http://localhost:8080/get_layout_manifest?role=employee")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
