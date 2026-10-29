#!/usr/bin/env python3
"""
Teste standalone do Hermes Bridge (MCP 2.x) — Cliente Remoto
===============================================================

Este teste verifica se o server.py (cliente MCP) consegue se comunicar com
o remote_hermes_api.py (servidor HTTP remoto).

IMPORTANTE: O servidor remoto deve estar rodando antes de executar este teste:
    python3 remote_hermes_api.py

Ou, na máquina remota (10.250.240.206):
    HERMES_API_PORT=8655 python3 remote_hermes_api.py
"""

import json
import subprocess
import sys
import time


def send_line(proc, obj: dict) -> None:
    line = json.dumps(obj) + "\n"
    proc.stdin.write(line.encode())
    proc.stdin.flush()


def read_line(proc) -> dict | None:
    raw = proc.stdout.readline()
    if not raw:
        return None
    try:
        return json.loads(raw.decode())
    except json.JSONDecodeError:
        print(f"  ⚠️  JSON inválido: {raw[:200]}")
        return None


def main() -> int:
    print("🚀 Testando Hermes Bridge MCP Server (Cliente Remoto)...")
    print("=" * 60)

    # Verifica se o servidor remoto está acessível
    print("📡 Verificando conectividade com servidor remoto...")
    import urllib.request
    try:
        req = urllib.request.Request("http://10.250.240.206:8655/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == "ok":
                print("   ✅ Servidor remoto respondendo!")
            else:
                print(f"   ⚠️  Health check retornou: {data}")
    except Exception as e:
        print(f"   ❌ Não consegui conectar ao servidor remoto: {e}")
        print("   📝 Certifique-se de que o remote_hermes_api.py está rodando em 10.250.240.206:8655")
        return 1

    # Inicia o server.py
    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/home/onclick/claude-hermes-bridge",
    )

    # 1) initialize
    print("\n📤 Enviando initialize...")
    send_line(proc, {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    })

    resp = read_line(proc)
    if not resp:
        print("❌ Sem resposta do initialize")
        proc.kill()
        return 1
    print(f"📥 OK — server: {resp.get('result', {}).get('serverInfo', {}).get('name', '?')}")

    # 2) notifications/initialized
    send_line(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

    # 3) tools/list
    print("📤 Listando tools...")
    send_line(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

    resp = read_line(proc)
    if not resp:
        print("❌ Sem resposta de tools/list")
        proc.kill()
        return 1

    tools = resp.get("result", {}).get("tools", [])
    print(f"📥 Tools registradas ({len(tools)}):")
    for t in tools:
        print(f"   • {t['name']}: {t.get('description', '')[:80]}...")

    # 4) Chama ask_hermes
    print("\n📤 Chamando ask_hermes (pode demorar ~30s)...")
    print("   Enviando pergunta para o servidor remoto 10.250.240.206:8655...")
    send_line(proc, {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "ask_hermes",
            "arguments": {
                "question": "Qual é o nome do banco de dados principal do KPL?",
                "project_dir": "/home/onclick/KPL",
            },
        },
    })

    resp = read_line(proc)
    if not resp:
        print("❌ Sem resposta de ask_hermes")
        proc.kill()
        return 1

    result = resp.get("result", {})
    contents = result.get("content", [])
    text = contents[0].get("text", "") if contents else ""
    print(f"📥 Resposta do Hermes (via servidor remoto):\n{'─' * 40}")
    print(text[:800] + ("..." if len(text) > 800 else ""))
    print("─" * 40)

    # 5) Cleanup
    proc.stdin.close()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    stderr = proc.stderr.read().decode()
    if stderr:
        print(f"\n⚠️  Stderr:\n{stderr[:500]}")

    if text and not text.startswith("[ERRO]"):
        print("\n✅ Teste passou! MCP Server conectou ao Hermes remoto com sucesso!")
        return 0
    else:
        print("\n❌ Teste falhou — verifique se o servidor remoto está rodando.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
