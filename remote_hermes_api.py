#!/usr/bin/env python3
"""
Hermes Remote API Server
========================
Roda na máquina que tem acesso ao Hermes (ex: 10.250.240.206).
Expõe um endpoint HTTP que recebe perguntas e retorna respostas do Hermes.

✅ Cache integrado — perguntas repetidas respondem instantaneamente.
✅ TTL configurável — respostas expiram após X minutos.

Uso:
    python3 remote_hermes_api.py

O servidor escuta em 0.0.0.0:8655 por padrão.
"""

import hashlib
import json
import os
import subprocess
import time
from collections import OrderedDict
from http.server import HTTPServer, BaseHTTPRequestHandler

HERMES_BIN = os.environ.get("HERMES_BIN", "hermes")
MAX_TURNS = int(os.environ.get("HERMES_MAX_TURNS", "20"))
API_PORT = int(os.environ.get("HERMES_API_PORT", "8655"))
CACHE_TTL_MINUTES = int(os.environ.get("HERMES_CACHE_TTL", "60"))  # 1 hora por padrão
CACHE_MAX_SIZE = int(os.environ.get("HERMES_CACHE_SIZE", "100"))

# ─── Cache em memória ─────────────────────────────────────────────────────────
# Chave: sha256(prompt + "|" + project_dir)
# Valor: {"response": str, "timestamp": float}
_cache: OrderedDict[str, dict] = OrderedDict()


def _cache_key(prompt: str, project_dir: str) -> str:
    return hashlib.sha256(f"{prompt}|{project_dir}".encode("utf-8")).hexdigest()


def _get_cached(prompt: str, project_dir: str) -> str | None:
    key = _cache_key(prompt, project_dir)
    if key not in _cache:
        return None

    entry = _cache[key]
    age_min = (time.time() - entry["timestamp"]) / 60

    if age_min > CACHE_TTL_MINUTES:
        del _cache[key]
        return None

    # Move para o fim (LRU — most recently used)
    _cache.move_to_end(key)
    return entry["response"]


def _set_cached(prompt: str, project_dir: str, response: str) -> None:
    # Não cacheia erros
    if response.startswith("[ERRO]"):
        return

    key = _cache_key(prompt, project_dir)
    _cache[key] = {"response": response, "timestamp": time.time()}
    _cache.move_to_end(key)

    # Evita crescimento ilimitado
    while len(_cache) > CACHE_MAX_SIZE:
        _cache.popitem(last=False)


def _cache_stats() -> dict:
    total = len(_cache)
    oldest = min(e["timestamp"] for e in _cache.values()) if _cache else 0
    return {
        "entries": total,
        "max_size": CACHE_MAX_SIZE,
        "ttl_minutes": CACHE_TTL_MINUTES,
        "oldest_entry_age_min": round((time.time() - oldest) / 60, 1) if oldest else 0,
    }


# ─── Hermes ─────────────────────────────────────────────────────────────────

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


# ─── HTTP Handler ─────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args) -> None:
        pass  # Silencia logs de acesso (barulho no terminal)

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "cache": _cache_stats()}).encode())
        elif self.path == "/cache/clear":
            _cache.clear()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "cache cleared"}).encode())
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

        # Verifica cache
        cached = _get_cached(prompt, project_dir)
        if cached is not None:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Cache", "HIT")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"response": cached, "cached": True}).encode())
            return

        # Chama Hermes
        response = call_hermes(prompt, project_dir)
        _set_cached(prompt, project_dir, response)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Cache", "MISS")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"response": response, "cached": False}).encode())


def main() -> None:
    print(f"🚀 Hermes Remote API rodando em http://0.0.0.0:{API_PORT}")
    print(f"   Health check:   curl http://localhost:{API_PORT}/health")
    print(f"   Limpar cache:   curl http://localhost:{API_PORT}/cache/clear")
    print(f"   Hermes bin:     {HERMES_BIN}")
    print(f"   Cache TTL:      {CACHE_TTL_MINUTES} minutos")
    print(f"   Cache max:      {CACHE_MAX_SIZE} entradas")
    print("   Pressione Ctrl+C para parar")
    server = HTTPServer(("0.0.0.0", API_PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Parando servidor...")
        server.shutdown()


if __name__ == "__main__":
    main()
