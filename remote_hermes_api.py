#!/usr/bin/env python3
"""
Hermes Remote API Server
========================
Roda na máquina que tem acesso ao Hermes (ex: 10.250.240.206).
Expõe endpoints HTTP que recebe perguntas e retorna respostas do Hermes.

✅ Cache integrado — perguntas repetidas respondem instantaneamente.
✅ TTL configurável — respostas expiram após X minutos.
✅ Controle de versão — header X-Server-Version em toda resposta.
✅ Health check detalhado — git status, cache, versão.
✅ Busca cross-project — git grep em todos os repos.

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
from pathlib import Path

HERMES_BIN = os.environ.get("HERMES_BIN", "hermes")
MAX_TURNS = int(os.environ.get("HERMES_MAX_TURNS", "40"))
API_PORT = int(os.environ.get("HERMES_API_PORT", "8655"))
CACHE_TTL_MINUTES = int(os.environ.get("HERMES_CACHE_TTL", "60"))
CACHE_MAX_SIZE = int(os.environ.get("HERMES_CACHE_SIZE", "100"))

# ─── Projetos conhecidos ───────────────────────────────────────────────────────
PROJECT_DIRS = {
    "KPL": Path.home() / "KPL",
    "OnclickERP": Path.home() / "OnclickERP",
    "apiecomm": Path.home() / "apiecomm",
    "hermes-bridge": Path.home() / "hermes-bridge",
}

# ─── Versão do servidor ───────────────────────────────────────────────────────
VERSION_FILE = Path(__file__).parent / "VERSION"
SERVER_VERSION = "0.0.0"
try:
    if VERSION_FILE.exists():
        SERVER_VERSION = VERSION_FILE.read_text().strip()
except Exception:
    pass

# ─── Cache em memória ─────────────────────────────────────────────────────────
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

    _cache.move_to_end(key)
    return entry["response"]


def _set_cached(prompt: str, project_dir: str, response: str) -> None:
    if response.startswith("[ERRO]"):
        return

    key = _cache_key(prompt, project_dir)
    _cache[key] = {"response": response, "timestamp": time.time()}
    _cache.move_to_end(key)

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


# ─── Git helpers ─────────────────────────────────────────────────────────────

def _run_git(path: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True, text=True
    )


def _find_git_repos(root: Path) -> list[Path]:
    repos = []
    if not root.exists():
        return repos
    if (root / ".git").exists():
        repos.append(root)
    for subdir in root.iterdir():
        if subdir.is_dir() and not subdir.name.startswith("."):
            if (subdir / ".git").exists():
                repos.append(subdir)
            for subsubdir in subdir.iterdir():
                if subsubdir.is_dir() and not subsubdir.name.startswith("."):
                    if (subsubdir / ".git").exists():
                        repos.append(subsubdir)
    seen = set()
    unique = []
    for p in repos:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            unique.append(p)
    return sorted(unique, key=lambda p: str(p))


def _repo_status(repo_path: Path) -> dict:
    result = _run_git(repo_path, "status", "--short")
    branch_result = _run_git(repo_path, "branch", "--show-current")
    branch = branch_result.stdout.strip() or "?"

    if result.returncode != 0:
        return {"path": str(repo_path), "branch": branch, "dirty": False, "error": result.stderr.strip()[:200]}

    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    return {
        "path": str(repo_path),
        "branch": branch,
        "dirty": len(lines) > 0,
        "changes": len(lines),
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
        pass

    def _send_json(self, status: int, data: dict, extra_headers: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Server-Version", SERVER_VERSION)
        self.send_header("Access-Control-Allow-Origin", "*")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _do_status(self) -> None:
        """Retorna status detalhado de todos os repositórios."""
        all_repos: list[Path] = []
        for name, path in PROJECT_DIRS.items():
            if path.exists() and (path / ".git").exists():
                all_repos.append(path)
            if name in ("OnclickERP", "apiecomm"):
                all_repos.extend(_find_git_repos(path))

        # Remove duplicatas
        seen = set()
        unique = []
        for p in all_repos:
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                unique.append(p)

        repo_statuses = [_repo_status(p) for p in unique]
        dirty_count = sum(1 for r in repo_statuses if r.get("dirty", False))

        self._send_json(200, {
            "status": "ok",
            "version": SERVER_VERSION,
            "cache": _cache_stats(),
            "total_repos": len(unique),
            "dirty_repos": dirty_count,
            "repositories": repo_statuses,
        })

    def _do_search(self, data: dict) -> None:
        """Busca uma string em todos os repositórios via git grep."""
        query = data.get("query", "").strip()
        if not query:
            self._send_json(400, {"error": "Campo 'query' é obrigatório"})
            return

        # Limita query a 100 chars e remove caracteres perigosos
        query = query[:100].replace("'", "").replace('"', "")

        all_results: list[dict] = []
        total_matches = 0

        for name, path in PROJECT_DIRS.items():
            if not path.exists():
                continue
            repos = [path] if (path / ".git").exists() else _find_git_repos(path)

            for repo_path in repos:
                result = subprocess.run(
                    ["git", "-C", str(repo_path), "grep", "-I", "-n", "-c", query],
                    capture_output=True, text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().splitlines()
                    match_count = sum(int(l.split(":")[-1]) for l in lines if ":" in l)
                    total_matches += match_count
                    rel = str(repo_path.relative_to(Path.home()))
                    all_results.append({
                        "repo": rel,
                        "matches": match_count,
                        "files_with_matches": len(lines),
                    })

        # Ordena por mais matches
        all_results.sort(key=lambda x: x["matches"], reverse=True)

        self._send_json(200, {
            "query": query,
            "total_matches": total_matches,
            "repos_searched": len(all_results),
            "results": all_results[:20],  # limita a 20
        })

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {
                "status": "ok",
                "version": SERVER_VERSION,
                "cache": _cache_stats(),
            })
        elif self.path == "/version":
            self._send_json(200, {"version": SERVER_VERSION})
        elif self.path == "/status":
            self._do_status()
        elif self.path == "/cache/clear":
            _cache.clear()
            self._send_json(200, {"status": "cache cleared"})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/ask":
            self._do_ask()
        elif self.path == "/search":
            self._do_post_search()
        else:
            self.send_response(404)
            self.end_headers()

    def _do_ask(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
        except (ValueError, json.JSONDecodeError) as e:
            self._send_json(400, {"error": f"JSON inválido: {e}"})
            return

        prompt = data.get("prompt", "")
        project_dir = data.get("project_dir", "")

        if not prompt:
            self._send_json(400, {"error": "Campo 'prompt' é obrigatório"})
            return

        # Verifica cache
        cached = _get_cached(prompt, project_dir)
        if cached is not None:
            self._send_json(200, {"response": cached, "cached": True, "version": SERVER_VERSION}, extra_headers={"X-Cache": "HIT"})
            return

        # Chama Hermes
        response = call_hermes(prompt, project_dir)
        _set_cached(prompt, project_dir, response)

        self._send_json(200, {"response": response, "cached": False, "version": SERVER_VERSION}, extra_headers={"X-Cache": "MISS"})

    def _do_post_search(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
        except (ValueError, json.JSONDecodeError) as e:
            self._send_json(400, {"error": f"JSON inválido: {e}"})
            return

        self._do_search(data)


def main() -> None:
    print(f"🚀 Hermes Remote API v{SERVER_VERSION} rodando em http://0.0.0.0:{API_PORT}")
    print(f"   Health check:   curl http://localhost:{API_PORT}/health")
    print(f"   Status:         curl http://localhost:{API_PORT}/status")
    print(f"   Busca:          POST http://localhost:{API_PORT}/search")
    print(f"   Versão:         curl http://localhost:{API_PORT}/version")
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
