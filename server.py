#!/usr/bin/env python3
"""
Hermes Bridge MCP Server — Cliente Remoto
==========================================
Roda na máquina do time (Mac/Windows/Linux) que usa Claude Code.

✅ Controle de versão — avisa se o cliente estiver desatualizado.
✅ Health check detalhado — status do servidor e repositórios.
✅ Busca cross-project — git grep em todos os projetos.

Configuração via HERMES_API_URL (padrão: http://10.250.240.206:8655).
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
_HISTORY: list[dict] = []
_MAX_HISTORY_LEN = 20
_VERSION_WARNING_SHOWN = False


def _call_remote(method: str, path: str, payload: dict | None = None) -> tuple[dict, str]:
    """Faz request HTTP para o servidor remoto e retorna (data, server_version)."""
    url = f"{HERMES_API_URL}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8") if payload else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            server_version = resp.headers.get("X-Server-Version", "0.0.0")
            data = json.loads(resp.read().decode("utf-8"))
            return data, server_version
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {"error": body[:500]}
        return data, "0.0.0"
    except urllib.error.URLError as e:
        return {"error": f"Não consegui conectar ao servidor em {HERMES_API_URL}. Detalhes: {e.reason}"}, "0.0.0"
    except Exception as e:
        return {"error": f"Falha na comunicação: {e}"}, "0.0.0"


def _check_version(server_version: str) -> str:
    global _VERSION_WARNING_SHOWN
    if _VERSION_WARNING_SHOWN or server_version == "0.0.0" or CLIENT_VERSION == "0.0.0":
        return ""
    if server_version != CLIENT_VERSION:
        _VERSION_WARNING_SHOWN = True
        return (
            f"\n\n⚠️ **ATUALIZAÇÃO DISPONÍVEL:** "
            f"Seu Hermes Bridge está na versão **{CLIENT_VERSION}** mas o servidor "
            f"remoto está na **{server_version}**. "
            f"Rode `python3 install.py --force` na pasta `~/hermes-bridge` para atualizar."
        )
    return ""


# ─── Builders ────────────────────────────────────────────────────────────────

def _build_prompt(question: str, extra_context: str = "") -> str:
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


def _build_status_summary(data: dict) -> str:
    """Monta resposta legível do endpoint /status."""
    lines: list[str] = ["## 📊 Status do Hermes Remoto"]
    lines.append(f"**Versão do servidor:** {data.get('version', '?')}")
    lines.append(f"**Repos monitorados:** {data.get('total_repos', 0)}")
    lines.append(f"**Repos com mudanças não commitadas:** {data.get('dirty_repos', 0)}")
    lines.append("")

    cache = data.get("cache", {})
    lines.append("### 🗂️ Cache")
    lines.append(f"- Entradas em cache: {cache.get('entries', 0)}")
    lines.append(f"- TTL: {cache.get('ttl_minutes', 0)} minutos")
    lines.append(f"- Máximo: {cache.get('max_size', 0)}")
    lines.append("")

    repos = data.get("repositories", [])
    if repos:
        lines.append("### 📦 Repositórios")
        dirty = [r for r in repos if r.get("dirty")]
        clean = [r for r in repos if not r.get("dirty")]

        if dirty:
            lines.append(f"**🟡 Com mudanças ({len(dirty)}):**")
            for r in dirty:
                rel = r["path"].replace(str(Path.home()), "~")
                lines.append(f"  - `{rel}` — branch `{r['branch']}` — {r['changes']} arquivo(s) alterado(s)")
        if clean:
            lines.append(f"**🟢 Atualizados ({len(clean)}):**")
            for r in clean[:5]:
                rel = r["path"].replace(str(Path.home()), "~")
                lines.append(f"  - `{rel}` — branch `{r['branch']}`")
            if len(clean) > 5:
                lines.append(f"  - ... e mais {len(clean) - 5}")
        lines.append("")

    return "\n".join(lines)


def _build_search_summary(data: dict, query: str) -> str:
    """Monta resposta legível do endpoint /search."""
    lines: list[str] = [f"## 🔍 Busca por: `{query}`"]
    lines.append(f"**Total de ocorrências:** {data.get('total_matches', 0)}")
    lines.append(f"**Repositórios encontrados:** {data.get('repos_searched', 0)}")
    lines.append("")

    results = data.get("results", [])
    if not results:
        lines.append("Nenhuma ocorrência encontrada.")
        return "\n".join(lines)

    lines.append("### 📁 Resultados por repositório")
    for r in results:
        repo = r["repo"]
        matches = r["matches"]
        files = r["files_with_matches"]
        lines.append(f"- **`{repo}`** — {matches} ocorrência(s) em {files} arquivo(s)")
    lines.append("")
    lines.append("> 💡 **Dica:** Use a tool `ask_hermes` com `project_dir` apontando para o repo específico para entender o contexto dessas ocorrências.")

    return "\n".join(lines)


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
    global _HISTORY, _VERSION_WARNING_SHOWN

    full_prompt = _build_prompt(question, context)
    data, server_version = _call_remote("POST", "/ask", {"prompt": full_prompt, "project_dir": project_dir})

    if "error" in data:
        return [TextContent(type="text", text=f"[ERRO] {data['error']}")]

    response = data.get("response", "[ERRO] Resposta vazia")

    if data.get("cached"):
        response = f"⚡ **(resposta em cache)**\n\n{response}"

    version_warning = _check_version(server_version)
    if version_warning:
        response += version_warning

    _HISTORY.append({"role": "user", "content": question})
    _HISTORY.append({"role": "assistant", "content": response})
    if len(_HISTORY) > _MAX_HISTORY_LEN:
        _HISTORY = _HISTORY[-_MAX_HISTORY_LEN:]

    return [TextContent(type="text", text=response)]


@server.tool(
    name="hermes_status",
    description=(
        "Verifica o status completo do servidor Hermes remoto: versão, cache, "
        "quais repositórios estão atualizados, quais têm mudanças não commitadas, etc. "
        "Use para diagnosticar problemas ou saber se o servidor está saudável."
    ),
)
def hermes_status() -> list[TextContent]:
    data, server_version = _call_remote("GET", "/status")

    if "error" in data:
        return [TextContent(type="text", text=f"[ERRO] {data['error']}")]

    summary = _build_status_summary(data)
    version_warning = _check_version(server_version)
    if version_warning:
        summary += version_warning

    return [TextContent(type="text", text=summary)]


@server.tool(
    name="search_all_projects",
    description=(
        "Busca uma palavra, procedure, tabela ou trecho de código em TODOS os projetos "
        "(KPL, OnclickERP, APIECOMM) usando git grep. Retorna quantas ocorrências "
        "existem em cada repositório. Use para localizar onde algo é usado no código. "
        "A busca é case-insensitive e ignora binários."
    ),
)
def search_all_projects(
    query: Annotated[str, "O termo a buscar. Ex: 'rpl.pStatusPedido', 'T_PEDIDO', 'Separar mercadorias'"],
) -> list[TextContent]:
    data, server_version = _call_remote("POST", "/search", {"query": query})

    if "error" in data:
        return [TextContent(type="text", text=f"[ERRO] {data['error']}")]

    summary = _build_search_summary(data, query)
    version_warning = _check_version(server_version)
    if version_warning:
        summary += version_warning

    return [TextContent(type="text", text=summary)]


@server.tool(
    name="clear_hermes_history",
    description="Limpa o histórico de conversa com o Hermes para esta sessão do Claude.",
)
def clear_hermes_history() -> list[TextContent]:
    global _HISTORY, _VERSION_WARNING_SHOWN
    _HISTORY = []
    _VERSION_WARNING_SHOWN = False
    return [TextContent(type="text", text="✅ Histórico do Hermes limpo para esta sessão.")]


# ─── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server.run()
