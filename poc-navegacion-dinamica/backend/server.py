import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from commands import handle_get_layout_manifest


class DispatcherHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Simulamos el endpoint /api/execute del sistema real
        if self.path == "/api/execute":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            command = data.get("command")
            params = data.get("params", {})

            print(f"Executing command: {command} with params: {params}")

            if command == "system.get_layout_manifest":
                result, status = handle_get_layout_manifest(params)
            else:
                result, status = {"error": "Comando no implementado en el PoC"}, 404

            self.send_response(status)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        # Manejo de CORS para el navegador
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def run():
    server_address = ("", 8080)
    httpd = HTTPServer(server_address, DispatcherHandler)
    print("🚀 PoC Dispatcher Backend corriendo en http://localhost:8080")
    print(
        "Endpoint: POST /api/execute { 'command': 'system.get_layout_manifest', 'params': { 'role': '...' } }"
    )
    httpd.serve_forever()


if __name__ == "__main__":
    run()
