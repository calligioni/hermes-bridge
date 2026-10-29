#!/usr/bin/env python3
"""
Hermes Bridge MCP Server — Cliente Remoto
==========================================
Roda na máquina do time (Mac/Windows/Linux) que usa Claude Code.

Este MCP Server NÃO roda o Hermes localmente. Ele é um cliente HTTP que
envia perguntas para um servidor remoto (ex: http://10.250.240.206:8655)
onde o Hermes está instalado com acesso ao código fonte.

✅ Controle de versão — avisa se o cliente estiver desatualizado.

Uso no Claude Code:
  "Pergunta pro Hermes qual é o banco principal do KPL"
  → Claude chama a tool ask_hermes
  → Este server faz POST para o servidor remoto
  → O servidor remoto roda hermes chat -q
  → Resposta volta pelo HTTP → aparece no chat do Claude

Configuração via variável de ambiente HERMES_API_URL (padrão: http://10.250.240.206:8655).
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import TextContent

# ─── Configuração ─────────────────────────────────────────────────────────────
HERMES_API_URL = os.environ.get(
    "HERMES_API_URL",
    "http://10.250.240.206:8655"
).rstrip("/")

# ─── Versão do cliente ────────────────────────────────────────────────────────
VERSION_FILE = Path(__file__).parent / "VERSION"
CLIENT_VERSION = "0.0.0"
try:
    if VERSION_FILE.exists():
        CLIENT_VERSION = VERSION_FILE.read_text().strip()
except Exception:
    pass

# ─── Estado por sessão ────────────────────────────────────────────────────────
_HISTORY: list[dict] = []  # [{"role": "user"/"assistant", "content": "..."}]
_MAX_HISTORY_LEN = 20      # 10 turnos
_VERSION_WARNING_SHOWN = False  # Mostra aviso de versão apenas uma vez


def _call_remote_hermes(prompt: str, project_dir: str = "") -> tuple[str, str, str]:
    """Faz POST para o servidor remoto e retorna (resposta, cache_status, server_version)."""
    url = f"{HERMES_API_URL}/ask"
    payload = json.dumps({
        "prompt": prompt,
        "project_dir": project_dir,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            cache_status = resp.headers.get("X-Cache", "UNKNOWN")
            data = json.loads(resp.read().decode("utf-8"))
            response = data.get("response", "[ERRO] Resposta vazia do servidor remoto")
            server_version = data.get("version", "0.0.0")
            return response, cache_status, server_version
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        return f"[ERRO] Servidor remoto retornou {e.code}: {body[:500]}", "ERROR", "0.0.0"
    except urllib.error.URLError as e:
        return (
            f"[ERRO] Não consegui conectar ao servidor remoto em {HERMES_API_URL}. "
            f"Verifique se a máquina remota está acessível e o servidor está rodando. "
            f"Detalhes: {e.reason}"
        ), "ERROR", "0.0.0"
    except Exception as e:
        return f"[ERRO] Falha na comunicação com servidor remoto: {e}", "ERROR", "0.0.0"


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


def _check_version(server_version: str) -> str:
    """Retorna aviso se o cliente estiver desatualizado."""
    global _VERSION_WARNING_SHOWN

    if _VERSION_WARNING_SHOWN:
        return ""

    if server_version == "0.0.0" or CLIENT_VERSION == "0.0.0":
        return ""  # Não conseguiu ler versão, ignora

    if server_version != CLIENT_VERSION:
        _VERSION_WARNING_SHOWN = True
        return (
            f"\n\n⚠️ **ATUALIZAÇÃO DISPONÍVEL:** "
            f"Seu Hermes Bridge está na versão **{CLIENT_VERSION}** mas o servidor "
            f"remoto está na **{server_version}**. "
            f"Rode `python3 install.py --force` na pasta `~/hermes-bridge` para atualizar."
        )

    return ""


# ─── Servidor MCP ─────────────────────────────────────────────────────────────

server = MCPServer(
    name="hermes-bridge",
    title="Hermes Bridge",
    description="Conecta Claude Code ao Hermes Agent remoto para análise profunda de código.",
    version=CLIENT_VERSION,
)


@server.tool(
    name="ask_hermes",
    description=(
        "Envia uma pergunta ao Hermes Agent (agente com acesso ao código fonte, "
        "graphify, skills e memória persistente). Use quando precisar de análise "
        "profunda do codebase, localização de procedures, entendimento de arquitetura, "
        "ou qualquer coisa relacionada aos projetos KPL / OnclickERP / APIECOMM. "
        "O Hermes mantém histórico de conversa entre chamadas na mesma sessão."
    ),
)
def ask_hermes(
    question: Annotated[str, "A pergunta ou tarefa para o Hermes. Ex: 'Qual o banco principal do KPL?'"],
    context: Annotated[str, "Contexto adicional (opcional). Ex: caminho de arquivo, trecho de código, erro."] = "",
    project_dir: Annotated[str, "Diretório base do projeto (opcional). Ex: /home/onclick/KPL, /home/onclick/OnclickERP, /home/onclick/apiecomm"] = "",
) -> list[TextContent]:
    """Pergunta algo ao Hermes remoto e retorna a resposta no chat do Claude."""
    global _HISTORY, _VERSION_WARNING_SHOWN

    full_prompt = _build_prompt(question, context)
    response, cache_status, server_version = _call_remote_hermes(full_prompt, project_dir)

    # Adiciona indicador de cache
    if cache_status == "HIT":
        response = f"⚡ **(resposta em cache)**\n\n{response}"

    # Verifica versão (mostra aviso apenas uma vez por sessão)
    version_warning = _check_version(server_version)
    if version_warning:
        response += version_warning

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
    global _HISTORY, _VERSION_WARNING_SHOWN
    _HISTORY = []
    _VERSION_WARNING_SHOWN = False
    return [TextContent(type="text", text="✅ Histórico do Hermes limpo para esta sessão.")]


# ─── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server.run()
