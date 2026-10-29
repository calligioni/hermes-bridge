#!/usr/bin/env python3
"""
Hermes Bridge — Script de Instalação Automática (macOS/Linux/Windows)
=====================================================================

Instala e configura o Hermes Bridge MCP Server para o Claude Code.

✅ Idempotente — pode rodar quantas vezes quiser (atualiza o que existe)
✅ macOS/Linux/Windows — detecta o SO automaticamente
✅ Não-interativo — com --yes ou --force, não pergunta nada
✅ Pergunta automaticamente os diretórios dos projetos

Uso interativo:
    python3 install.py

Uso automático (Claude Code):
    python3 install.py --yes

Ou via Claude Code:
    "Roda o install.py do repo calligioni/hermes-bridge com --yes"
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def print_step(n: int, total: int, msg: str) -> None:
    print(f"\n{'='*60}")
    print(f"📍 PASSO {n}/{total}: {msg}")
    print('='*60)


def ask(question: str, default: str = "") -> str:
    if default:
        prompt = f"{question} [{default}]: "
    else:
        prompt = f"{question}: "
    answer = input(prompt).strip()
    return answer if answer else default


def ask_yes_no(question: str, default: bool = True, auto_yes: bool = False) -> bool:
    if auto_yes:
        return True
    suffix = " [Y/n]: " if default else " [y/N]: "
    answer = input(f"{question}{suffix}").strip().lower()
    if not answer:
        return default
    return answer in ('y', 'yes', 's', 'sim')


def find_hermes() -> str | None:
    """Procura o binário hermes no PATH e em locais comuns."""
    hermes_path = shutil.which("hermes")
    if hermes_path:
        return hermes_path
    home = Path.home()
    candidates = [
        home / ".local" / "bin" / "hermes",
        home / "bin" / "hermes",
        Path("/usr/local/bin/hermes"),
        Path("/usr/bin/hermes"),
        Path("/opt/hermes/bin/hermes"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def get_system() -> str:
    """Retorna 'macos', 'linux' ou 'windows'."""
    s = platform.system().lower()
    if s == "darwin":
        return "macos"
    return s


def get_claude_config_path() -> Path:
    """Retorna o caminho do claude_desktop_config.json no SO atual."""
    system = get_system()
    home = Path.home()
    if system == "macos":
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "linux":
        return home / ".config" / "claude" / "claude_desktop_config.json"
    elif system == "windows":
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    return home / ".config" / "claude" / "claude_desktop_config.json"


def get_venv_python(venv_dir: Path) -> Path:
    """Retorna o caminho do Python no virtualenv para o SO atual."""
    if get_system() == "windows":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def get_path_separator() -> str:
    """Retorna o separador de PATH do SO."""
    return ";" if get_system() == "windows" else ":"


def detect_project_dirs() -> dict[str, str | None]:
    """Tenta detectar automaticamente os diretórios dos projetos."""
    home = Path.home()
    projects: dict[str, str | None] = {
        "KPL": None,
        "OnclickERP": None,
        "apiecomm": None,
    }
    for name in projects:
        if (home / name).exists():
            projects[name] = str(home / name)
    return projects


def ensure_dir(path: Path) -> None:
    """Cria diretórios intermediários se não existirem."""
    path.mkdir(parents=True, exist_ok=True)


def install_deps(venv_python: Path, install_dir: Path) -> bool:
    """Instala/atualiza dependências no virtualenv."""
    req_file = install_dir / "requirements.txt"
    if not req_file.exists():
        print(f"   ❌ {req_file} não encontrado")
        return False
    result = run([str(venv_python), "-m", "pip", "install", "-q", "-r", str(req_file)])
    if result.returncode != 0:
        print(f"   ❌ pip install falhou: {result.stderr[:300]}")
        return False
    return True


def update_repo(install_dir: Path, repo_url: str, auto_yes: bool) -> bool:
    """
    Garante que o repositório está clonado e atualizado.
    Se já existe: faz git pull. Se não: clona.
    """
    if install_dir.exists() and (install_dir / ".git").exists():
        print(f"   📦 Repositório já existe em {install_dir}")
        print("   🔄 Fazendo git pull para atualizar...")
        result = run(["git", "-C", str(install_dir), "pull"])
        if result.returncode != 0:
            print(f"   ⚠️  git pull falhou: {result.stderr[:300]}")
            print("   Continuando com versão local...")
        else:
            print("   ✅ Repositório atualizado")
        return True
    elif install_dir.exists():
        # Diretório existe mas não é um git repo
        if not auto_yes:
            if ask_yes_no(f"   {install_dir} existe mas não é um git repo. Remover?", default=True, auto_yes=auto_yes):
                shutil.rmtree(install_dir)
            else:
                print("   ❌ Instalação cancelada — diretório existe e não é git repo")
                return False
        else:
            print(f"   🔄 Removendo diretório existente (modo automático)...")
            shutil.rmtree(install_dir)

    print(f"   📥 Clonando {repo_url} ...")
    result = run(["git", "clone", "--depth", "1", repo_url, str(install_dir)])
    if result.returncode != 0:
        print(f"   ❌ git clone falhou: {result.stderr[:500]}")
        return False
    print("   ✅ Repositório clonado")
    return True


def ensure_venv(venv_dir: Path, auto_yes: bool) -> bool:
    """
    Garante que o virtualenv existe.
    Se existe: mantém. Se não: cria.
    Com --force: recria.
    """
    if venv_dir.exists():
        venv_python = get_venv_python(venv_dir)
        if venv_python.exists():
            print(f"   ✅ Virtualenv já existe em {venv_dir}")
            return True
        # Diretório existe mas Python não — corrompido
        print(f"   ⚠️  Virtualenv parece corrompido, recriando...")
        shutil.rmtree(venv_dir)
    else:
        print(f"   🐍 Criando virtualenv em {venv_dir}...")

    result = run([sys.executable, "-m", "venv", str(venv_dir)])
    if result.returncode != 0:
        print(f"   ❌ Falha ao criar virtualenv: {result.stderr[:300]}")
        return False
    print("   ✅ Virtualenv criado")
    return True


def write_claude_config(config_path: Path, venv_python: Path, install_dir: Path, hermes_dir: str) -> None:
    """Escreve (ou atualiza) o claude_desktop_config.json."""
    # PATH: inclui o diretório do hermes + PATH atual
    sep = get_path_separator()
    path_parts = list(dict.fromkeys(
        [p for p in os.environ.get("PATH", "").split(sep) if p]
    ))
    if hermes_dir and hermes_dir not in path_parts:
        path_parts.insert(0, hermes_dir)
    path_env = sep.join(path_parts)

    new_entry = {
        "command": str(venv_python),
        "args": [str(install_dir / "server.py")],
        "env": {
            "HERMES_BIN": "hermes",
            "HERMES_MAX_TURNS": "20",
            "PATH": path_env,
        }
    }

    config: dict = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            print("   ⚠️  Config existente corrompida, criando nova...")
            config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Se já existe hermes-bridge, atualiza; senão, cria
    config["mcpServers"]["hermes-bridge"] = new_entry

    ensure_dir(config_path.parent)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Instala o Hermes Bridge MCP Server para Claude Code"
    )
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Responde 'sim' para todas as perguntas (modo automático)")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Força reinstalação completa (remove e recria)")
    args = parser.parse_args()

    auto_yes = args.yes or args.force

    print("""
╔══════════════════════════════════════════════════════════════╗
║     🔗 Hermes Bridge — Instalador Automático                 ║
║     Conecta Claude Code ao Hermes Agent                     ║
╚══════════════════════════════════════════════════════════════╝
""")

    total_steps = 8
    system = get_system()
    print(f"   SO detectado: {system.upper()}")

    # ═══════════════════════════════════════════════════════════
    # PASSO 1: Verificar SO
    # ═══════════════════════════════════════════════════════════
    print_step(1, total_steps, "Verificando ambiente")
    if system not in ("linux", "macos", "windows"):
        print(f"   ⚠️  SO '{system}' não testado. Tentando continuar...")

    # ═══════════════════════════════════════════════════════════
    # PASSO 2: Verificar Python
    # ═══════════════════════════════════════════════════════════
    print_step(2, total_steps, "Verificando Python")
    py_version = sys.version_info
    print(f"   Python: {py_version.major}.{py_version.minor}.{py_version.micro}")
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 12):
        print("   ❌ ERRO: Python 3.12+ é necessário.")
        return 1
    print("   ✅ Python OK")

    # ═══════════════════════════════════════════════════════════
    # PASSO 3: Verificar Git
    # ═══════════════════════════════════════════════════════════
    print_step(3, total_steps, "Verificando Git")
    git_result = run(["git", "--version"])
    if git_result.returncode != 0:
        print("   ❌ Git não encontrado. Instale o Git e tente novamente.")
        return 1
    print(f"   ✅ Git: {git_result.stdout.strip()}")

    # ═══════════════════════════════════════════════════════════
    # PASSO 4: Verificar Hermes
    # ═══════════════════════════════════════════════════════════
    print_step(4, total_steps, "Verificando Hermes Agent")
    hermes_path = find_hermes()
    hermes_dir = ""
    if hermes_path:
        print(f"   ✅ Hermes: {hermes_path}")
        hermes_dir = str(Path(hermes_path).parent)
    else:
        print("   ❌ Hermes NÃO encontrado.")
        if auto_yes:
            print("   ⚠️  Modo automático: assumindo ~/.local/bin")
            hermes_dir = str(Path.home() / ".local" / "bin")
        else:
            if ask_yes_no("   Hermes não encontrado. Deseja continuar?", default=False):
                hermes_dir = ask("Diretório do hermes", default=str(Path.home() / ".local" / "bin"))
            else:
                print("   🛑 Cancelado. Instale o Hermes: https://hermes-agent.nousresearch.com/docs/")
                return 1

    # ═══════════════════════════════════════════════════════════
    # PASSO 5: Diretórios dos projetos
    # ═══════════════════════════════════════════════════════════
    print_step(5, total_steps, "Configurando diretórios dos projetos")
    print("   O Hermes precisa acessar os códigos fonte.")
    detected = detect_project_dirs()
    project_dirs: dict[str, str] = {}
    for name, default_path in detected.items():
        if default_path:
            print(f"   ✅ {name}: encontrado em {default_path}")
            if auto_yes or ask_yes_no(f"   Confirmar {name}?", default=True, auto_yes=auto_yes):
                project_dirs[name] = default_path
            else:
                custom = ask(f"   Caminho para {name}", default="")
                if custom:
                    project_dirs[name] = custom
        else:
            print(f"   ❓ {name}: não encontrado")
            if auto_yes:
                print("   (pulando — modo automático)")
            else:
                custom = ask(f"   Caminho para {name} (vazio = pular)", default="")
                if custom:
                    project_dirs[name] = custom

    # ═══════════════════════════════════════════════════════════
    # PASSO 6: Clonar/Atualizar repositório e criar venv
    # ═══════════════════════════════════════════════════════════
    print_step(6, total_steps, "Instalando Hermes Bridge")
    repo_url = "https://github.com/calligioni/hermes-bridge.git"
    install_dir = Path.home() / "hermes-bridge"
    venv_dir = install_dir / ".venv"

    # Se --force, remove tudo antes
    if args.force and install_dir.exists():
        print(f"   🔄 --force ativo: removendo {install_dir} ...")
        shutil.rmtree(install_dir)

    # Atualiza ou clona o repo
    if not update_repo(install_dir, repo_url, auto_yes):
        return 1

    # Garante virtualenv
    if not ensure_venv(venv_dir, auto_yes):
        return 1

    # Instala dependências
    venv_python = get_venv_python(venv_dir)
    print(f"   📦 Instalando dependências...")
    if not install_deps(venv_python, install_dir):
        return 1
    print("   ✅ Dependências OK")

    # ═══════════════════════════════════════════════════════════
    # PASSO 7: Configurar Claude Code
    # ═══════════════════════════════════════════════════════════
    print_step(7, total_steps, "Configurando Claude Code MCP")
    config_path = get_claude_config_path()
    print(f"   Config: {config_path}")
    write_claude_config(config_path, venv_python, install_dir, hermes_dir)
    print(f"   ✅ Configuração salva")

    # ═══════════════════════════════════════════════════════════
    # PASSO 8: Testar
    # ═══════════════════════════════════════════════════════════
    print_step(8, total_steps, "Testando instalação")
    print("   🧪 Rodando test_server.py...")
    test_result = run([str(venv_python), str(install_dir / "test_server.py")], timeout=120)
    if test_result.returncode == 0:
        print("   ✅ Teste passou!")
    else:
        print("   ⚠️  Teste não passou (pode ser normal se Hermes não configurado)")
        # Mostra só as primeiras linhas do erro
        err_lines = test_result.stderr.strip().splitlines()
        if err_lines:
            print(f"   Erro: {err_lines[0][:200]}")

    # ═══════════════════════════════════════════════════════════
    # RESUMO
    # ═══════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("🎉 INSTALAÇÃO CONCLUÍDA!")
    print("="*60)
    print()
    print(f"📁 Instalação:   {install_dir}")
    print(f"🐍 Python venv:   {venv_python}")
    print(f"⚙️  Config Claude: {config_path}")
    print()
    if project_dirs:
        print("📁 Projetos:")
        for name, path in project_dirs.items():
            print(f"   • {name}: {path}")
    print()
    print("📋 Próximos passos:")
    print("   1. REINICIE o Claude Code (feche e abra novamente)")
    print("   2. Digite: Pergunta pro Hermes qual é o banco do KPL")
    print()
    print("🔗 Repo: https://github.com/calligioni/hermes-bridge")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Cancelado pelo usuário.")
        sys.exit(130)
