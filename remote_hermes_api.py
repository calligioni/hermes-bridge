#!/usr/bin/env python3
"""
Hermes Remote API Server
========================
Roda na máquina que tem acesso ao Hermes (ex: 10.250.240.206).
Expõe um endpoint HTTP que recebe perguntas e retorna respostas do Hermes.

Uso:
    python3 remote_hermes_api.py

O servidor escuta em 0.0.0.0:8655 por padrão.
"""

import json
import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

HERMES_BIN = os.environ.get("HERMES_BIN", "hermes")
MAX_TURNS = int(os.environ.get("HERMES_MAX_TURNS", "20"))
API_PORT = int(os.environ.get("HERMES_API_PORT", "8655"))

def call_hermes(prompt: str, project_dir: str = "") -> str:
    """Executa hermes chat -q e retorna a resposta limpa."""
    cmd = [
        HERMES_BIN, "chat", "-q", prompt,
        "--quiet", "--source", "tool",
        "--max-turns", str(MAX_TURNS),
    ]
    if project_dir:
        cmd.extend(["--in", project_dir])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
            env={**os.environ, "FORCE_COLOR": "0", "NO_COLOR": "1"},
        )
    except subprocess.TimeoutExpired:
        return "[ERRO] Timeout: o Hermes demorou mais de 5 minutos."
    except FileNotFoundError:
        return f"[ERRO] '{HERMES_BIN}' não encontrado. Verifique se o Hermes está no PATH."

    output = result.stdout.strip()

    # Remove cabeçalho "session_id:" que o --quiet às vezes imprime
    if "session_id:" in output:
        lines = output.splitlines()
        filtered = []
        skip = True
        for line in lines:
            if skip and line.startswith("session_id:"):
                skip = False
                continue
            if skip and not line.strip():
                continue
            skip = False
            filtered.append(line)
        output = "\n".join(filtered).strip()

    if result.returncode != 0:
        err = result.stderr.strip() or output or "Erro desconhecido"
        return f"[ERRO] Código {result.returncode}: {err}"

    return output if output else "[ERRO] Resposta vazia."


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args) -> None:
        pass  # Silencia logs de acesso (barulho no terminal)

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        if self.path != "/ask":
            self.send_response(404)
            self.end_headers()
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
        except (ValueError, json.JSONDecodeError) as e:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"JSON inválido: {e}"}).encode())
            return

        prompt = data.get("prompt", "")
        project_dir = data.get("project_dir", "")

        if not prompt:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Campo 'prompt' é obrigatório"}).encode())
            return

        response = call_hermes(prompt, project_dir)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")  # CORS para facilitar
        self.end_headers()
        self.wfile.write(json.dumps({"response": response}).encode())


def main() -> None:
    server = HTTPServer(("0.0.0.0", API_PORT), Handler)
    print(f"🚀 Hermes Remote API rodando em http://0.0.0.0:{API_PORT}")
    print(f"   Health check: curl http://localhost:{API_PORT}/health")
    print(f"   Hermes bin:   {HERMES_BIN}")
    print("   Pressione Ctrl+C para parar")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Parando servidor...")
        server.shutdown()


if __name__ == "__main__":
    main()
