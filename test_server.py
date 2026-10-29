#!/usr/bin/env python3
"""
Teste standalone do Hermes Bridge (MCP 2.x)
===========================================
Valida que o server.py inicializa corretamente e responde a uma tool call.
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
    print("🚀 Testando Hermes Bridge MCP Server...")
    print("=" * 60)

    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/home/onclick/claude-hermes-bridge",
    )

    # 1) initialize
    print("📤 Enviando initialize...")
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
    print(f"📥 Resposta do Hermes:\n{'─' * 40}")
    print(text[:800] + ("..." if len(text) > 800 else ""))
    print("─" * 40)

    # 5) Cleanup
    proc.stdin.close()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    # stderr
    stderr = proc.stderr.read().decode()
    if stderr:
        print(f"\n⚠️  Stderr:\n{stderr[:500]}")

    print("\n✅ Teste finalizado com sucesso!" if text else "\n❌ Teste falhou — resposta vazia.")
    return 0 if text else 1


if __name__ == "__main__":
    sys.exit(main())
