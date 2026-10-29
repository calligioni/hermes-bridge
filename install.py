#!/usr/bin/env python3
"""
Hermes Bridge — Script de Instalação Automática (Cliente Remoto)
=================================================================

Instala o Hermes Bridge MCP Server na MÁQUINA CLIENTE (Mac/Windows/Linux).
Este script NÃO instala o Hermes — ele configura o cliente para se conectar
a um servidor remoto onde o Hermes está rodando.

Arquitetura:
    ┌─────────────────┐         HTTP POST        ┌─────────────────────────┐
    │  Máquina Cliente│  ──────────────────────▶ │  Máquina Remota         │
    │  (Mac/Win/Linux)│    pergunta → resposta   │  (10.250.240.206)      │
    │                 │                         │  Hermes + Código Fonte  │
    │  Claude Code ──▶│    MCP tool ask_hermes   │  remote_hermes_api.py   │
    │  server.py      │  ──────────────────────▶ │  (servidor HTTP)        │
    └─────────────────┘                         └─────────────────────────┘

Uso:
    python3 install.py                    # Modo interativo (pergunta IP)
    python3 install.py --yes              # Modo automático (usa IP padrão)
    python3 install.py --yes --remote-ip 10.250.240.206  # Especifica IP
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


def get_system() -> str:
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
    if get_system() == "windows":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def install_deps(venv_python: Path, install_dir: Path) -> bool:
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
        if not auto_yes:
            if ask_yes_no(f"   {install_dir} existe mas não é um git repo. Remover?", default=True, auto_yes=auto_yes):
                shutil.rmtree(install_dir)
            else:
                print("   ❌ Cancelado — diretório existe e não é git repo")
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


def ensure_venv(venv_dir: Path) -> bool:
    if venv_dir.exists():
        venv_python = get_venv_python(venv_dir)
        if venv_python.exists():
            print(f"   ✅ Virtualenv já existe em {venv_dir}")
            return True
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


def write_claude_config(config_path: Path, venv_python: Path, install_dir: Path, remote_url: str) -> None:
    """Escreve (ou atualiza) o claude_desktop_config.json."""
    new_entry = {
        "command": str(venv_python),
        "args": [str(install_dir / "server.py")],
        "env": {
            "HERMES_API_URL": remote_url,
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

    config["mcpServers"]["hermes-bridge"] = new_entry

    ensure_dir(config_path.parent)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def test_remote_connection(remote_url: str) -> bool:
    """Testa se o servidor remoto está acessível."""
    import urllib.request
    health_url = f"{remote_url}/health"
    try:
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("status") == "ok"
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Instala o Hermes Bridge MCP Server (cliente remoto) para Claude Code"
    )
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Responde 'sim' para todas as perguntas (modo automático)")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Força reinstalação completa")
    parser.add_argument("--remote-ip", default="10.250.240.206",
                        help="IP da máquina remota onde o Hermes está rodando (padrão: 10.250.240.206)")
    parser.add_argument("--remote-port", default="8655",
                        help="Porta do servidor remoto (padrão: 8655)")
    args = parser.parse_args()

    auto_yes = args.yes or args.force
    remote_url = f"http://{args.remote_ip}:{args.remote_port}"

    print("""
╔══════════════════════════════════════════════════════════════╗
║     🔗 Hermes Bridge — Instalador Automático (Cliente)         ║
║     Conecta Claude Code ao Hermes remoto                    ║
╚══════════════════════════════════════════════════════════════╝
""")

    total_steps = 7
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
    # PASSO 4: Configurar servidor remoto
    # ═══════════════════════════════════════════════════════════
    print_step(4, total_steps, "Configurando servidor remoto")
    print("   Este MCP Server é um CLIENTE — ele se conecta a um servidor remoto")
    print("   onde o Hermes está instalado com acesso ao código fonte.")
    print()

    if auto_yes:
        print(f"   Modo automático: usando servidor remoto em {remote_url}")
    else:
        print(f"   Servidor remoto padrão: {remote_url}")
        custom_ip = ask("Digite o IP da máquina remota (ou Enter para usar o padrão)", default=args.remote_ip)
        custom_port = ask("Digite a porta (ou Enter para usar o padrão)", default=args.remote_port)
        remote_url = f"http://{custom_ip}:{custom_port}"
        print(f"   Servidor remoto configurado: {remote_url}")

    # Testa conectividade
    print(f"   🌐 Testando conexão com {remote_url}...")
    if test_remote_connection(remote_url):
        print("   ✅ Servidor remoto está ONLINE e respondendo!")
    else:
        print(f"   ⚠️  Não consegui conectar a {remote_url}")
        print("   Isso é NORMAL se o servidor ainda não foi iniciado.")
        print()
        print("   📝 INSTRUÇÕES PARA O ADMIN DA MÁQUINA REMOTA:")
        print("      1. Acesse a máquina remota (ex: via SSH)")
        print(f"      2. Clone o repo: git clone https://github.com/calligioni/hermes-bridge.git")
        print("      3. Rode o servidor: python3 remote_hermes_api.py")
        print(f"      4. O servidor vai escutar em 0.0.0.0:{args.remote_port}")
        print()
        if not auto_yes:
            if not ask_yes_no("Deseja continuar a instalação mesmo assim?", default=True):
                print("   🛑 Cancelado.")
                return 1

    # ═══════════════════════════════════════════════════════════
    # PASSO 5: Clonar/Atualizar repositório e criar venv
    # ═══════════════════════════════════════════════════════════
    print_step(5, total_steps, "Instalando Hermes Bridge")
    repo_url = "https://github.com/calligioni/hermes-bridge.git"
    install_dir = Path.home() / "hermes-bridge"
    venv_dir = install_dir / ".venv"

    if args.force and install_dir.exists():
        print(f"   🔄 --force: removendo {install_dir} ...")
        shutil.rmtree(install_dir)

    if not update_repo(install_dir, repo_url, auto_yes):
        return 1

    if not ensure_venv(venv_dir):
        return 1

    venv_python = get_venv_python(venv_dir)
    print(f"   📦 Instalando dependências...")
    if not install_deps(venv_python, install_dir):
        return 1
    print("   ✅ Dependências OK")

    # ═══════════════════════════════════════════════════════════
    # PASSO 6: Configurar Claude Code
    # ═══════════════════════════════════════════════════════════
    print_step(6, total_steps, "Configurando Claude Code MCP")
    config_path = get_claude_config_path()
    print(f"   Config: {config_path}")
    write_claude_config(config_path, venv_python, install_dir, remote_url)
    print(f"   ✅ Configuração salva (HERMES_API_URL={remote_url})")

    # ═══════════════════════════════════════════════════════════
    # PASSO 7: Testar MCP Server localmente
    # ═══════════════════════════════════════════════════════════
    print_step(7, total_steps, "Testando instalação")
    print("   🧪 Rodando test_server.py...")
    test_result = run([str(venv_python), str(install_dir / "test_server.py")], timeout=120)
    if test_result.returncode == 0:
        print("   ✅ Teste passou!")
    else:
        print("   ⚠️  Teste não passou (pode ser normal se servidor remoto não está rodando)")
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
    print(f"📁 Instalação:    {install_dir}")
    print(f"🐍 Python venv:    {venv_python}")
    print(f"⚙️  Config Claude:  {config_path}")
    print(f"🌐 Servidor remoto: {remote_url}")
    print()
    print("📋 Próximos passos:")
    print("   1. REINICIE o Claude Code (feche e abra novamente)")
    print("   2. No chat, digite: Pergunta pro Hermes qual é o banco do KPL")
    print()
    print("📝 IMPORTANTE:")
    print("   Certifique-se de que o servidor remoto está rodando:")
    print(f"      ssh <usuario>@{args.remote_ip}")
    print("      cd ~/hermes-bridge && python3 remote_hermes_api.py")
    print()
    print("🔗 Repo: https://github.com/calligioni/hermes-bridge")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Cancelado pelo usuário.")
        sys.exit(130)
