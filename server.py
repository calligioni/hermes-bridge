#!/usr/bin/env python3
"""
Hermes Bridge MCP Server — MCP 2.x
===================================
Conecta Claude Code ao Hermes Agent via Model Context Protocol.

O Claude Code inicia este servidor automaticamente via stdio.
Cada sessão do Claude = uma instância deste servidor = histórico isolado.

Uso no Claude Code:
  "Pergunta pro Hermes qual é o banco principal do KPL"
  → Claude chama a tool `ask_hermes`
  → Hermes processa e responde
  → Resposta aparece no chat do Claude
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import TextContent

# ─── Configuração ─────────────────────────────────────────────────────────────
HERMES_BIN = os.environ.get("HERMES_BIN", "hermes")
MAX_TURNS = int(os.environ.get("HERMES_MAX_TURNS", "20"))

# ─── Estado por sessão ────────────────────────────────────────────────────────
# Cada instância do servidor MCP = uma sessão do Claude → histórico isolado.
_HISTORY: list[dict] = []  # [{"role": "user"/"assistant", "content": "..."}]
_MAX_HISTORY_LEN = 20      # 10 turnos (user + assistant)


def _call_hermes(prompt: str, project_dir: str = "") -> str:
    """Executa `hermes chat -q` e retorna a resposta limpa."""
    cwd = project_dir if project_dir and Path(project_dir).exists() else None

    cmd = [
        HERMES_BIN,
        "chat",
        "-q", prompt,
        "--quiet",
        "--source", "tool",
        "--max-turns", str(MAX_TURNS),
    ]
    if cwd:
        cmd.extend(["--in", str(cwd)])

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "FORCE_COLOR": "0", "NO_COLOR": "1"},
        )
    except subprocess.TimeoutExpired:
        return (
            "[ERRO] O Hermes demorou mais de 5 minutos para responder. "
            "Tente uma pergunta mais específica."
        )
    except FileNotFoundError:
        return (
            f"[ERRO] Comando '{HERMES_BIN}' não encontrado. "
            "Verifique se o Hermes está instalado e no PATH."
        )

    output = result.stdout.strip()

    # Remove o cabeçalho "session_id: XXX" que o --quiet às vezes imprime
    if "session_id:" in output:
        lines = output.splitlines()
        # session_id costuma estar nas primeiras linhas
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
        return f"[ERRO] Hermes retornou código {result.returncode}: {err}"

    if not output:
        return "[ERRO] Hermes não retornou nenhuma resposta."

    return output


def _build_prompt(question: str, extra_context: str = "") -> str:
    """Monta o prompt final juntando histórico + contexto + pergunta nova."""
    parts: list[str] = []

    if _HISTORY:
        parts.append("=== HISTÓRICO DA CONVERSA ===")
        for msg in _HISTORY:
            label = "Usuário" if msg["role"] == "user" else "Hermes"
            parts.append(f"{label}: {msg['content']}")
        parts.append("=== FIM DO HISTÓRICO ===\n")

    if extra_context:
        parts.append(f"=== CONTEXTO ADICIONAL ===\n{extra_context}\n=== FIM DO CONTEXTO ===\n")

    parts.append(f"=== NOVA PERGUNTA ===\n{question}")
    return "\n".join(parts)


# ─── Servidor MCP ─────────────────────────────────────────────────────────────

server = MCPServer(
    name="hermes-bridge",
    title="Hermes Bridge",
    description="Conecta Claude Code ao Hermes Agent para análise profunda de código.",
    version="1.0.0",
)


@server.tool(
    name="ask_hermes",
    description=(
        "Envia uma pergunta ao Hermes Agent (agente com acesso ao código fonte, "
        "graphify, skills e memória persistente). Use quando precisar de análise "
        "profunda do codebase, localização de procedures, entendimento de arquitetura, "
        "ou qualquer coisa relacionada aos projetos KPL/OnclickERP/APIECOMM. "
        "O Hermes mantém histórico de conversa entre chamadas na mesma sessão."
    ),
)
def ask_hermes(
    question: Annotated[str, "A pergunta ou tarefa para o Hermes. Ex: 'Qual o banco principal do KPL?'"],
    context: Annotated[str, "Contexto adicional (opcional). Ex: caminho de arquivo, trecho de código, erro."] = "",
    project_dir: Annotated[str, "Diretório base do projeto (opcional). Ex: /home/onclick/KPL, /home/onclick/OnclickERP"] = "",
) -> list[TextContent]:
    """Pergunta algo ao Hermes e retorna a resposta no chat do Claude."""
    global _HISTORY

    # Monta prompt com histórico
    full_prompt = _build_prompt(question, context)

    # Chama o Hermes
    response = _call_hermes(full_prompt, project_dir)

    # Atualiza histórico
    _HISTORY.append({"role": "user", "content": question})
    _HISTORY.append({"role": "assistant", "content": response})
    if len(_HISTORY) > _MAX_HISTORY_LEN:
        _HISTORY = _HISTORY[-_MAX_HISTORY_LEN:]

    return [TextContent(type="text", text=response)]


@server.tool(
    name="clear_hermes_history",
    description="Limpa o histórico de conversa com o Hermes para esta sessão do Claude.",
)
def clear_hermes_history() -> list[TextContent]:
    """Limpa o histórico de conversa acumulado com o Hermes."""
    global _HISTORY
    _HISTORY = []
    return [TextContent(type="text", text="✅ Histórico do Hermes limpo para esta sessão.")]


# ─── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server.run()
