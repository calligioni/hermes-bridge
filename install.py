#!/usr/bin/env python3
"""
Hermes Bridge — Script de Instalação Automática
================================================

Este script instala e configura o Hermes Bridge MCP Server para o Claude Code.

Funcionalidades:
- Detecta o sistema operacional
- Verifica pré-requisitos (Python, Git, Hermes)
- Cria virtualenv e instala dependências
- Descobre automaticamente onde está o hermes
- Pergunta os diretórios dos projetos (KPL, OnclickERP, APIECOMM)
- Configura automaticamente o claude_desktop_config.json
- Testa a conexão com o Hermes

Uso:
    python3 install.py

Ou via Claude Code:
    "Roda o install.py do repositório hermes-bridge para instalar tudo"
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Executa um comando e retorna o resultado."""
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def print_step(n: int, total: int, msg: str) -> None:
    """Printa um passo formatado."""
    print(f"\n{'='*60}")
    print(f"📍 PASSO {n}/{total}: {msg}")
    print('='*60)


def ask(question: str, default: str = "") -> str:
    """Pergunta algo ao usuário."""
    if default:
        prompt = f"{question} [{default}]: "
    else:
        prompt = f"{question}: "
    answer = input(prompt).strip()
    return answer if answer else default


def ask_yes_no(question: str, default: bool = True) -> bool:
    """Pergunta sim/não."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    answer = input(f"{question}{suffix}").strip().lower()
    if not answer:
        return default
    return answer in ('y', 'yes', 's', 'sim')


def find_hermes() -> str | None:
    """Tenta encontrar o binário hermes no sistema."""
    hermes_path = shutil.which("hermes")
    if hermes_path:
        return hermes_path
    # Tenta locais comuns
    common_paths = [
        Path.home() / ".local" / "bin" / "hermes",
        Path("/usr/local/bin/hermes"),
        Path("/usr/bin/hermes"),
        Path("/opt/hermes/bin/hermes"),
    ]
    for p in common_paths:
        if p.exists():
            return str(p)
    return None


def get_claude_config_path() -> Path:
    """Retorna o caminho do arquivo de configuração do Claude Code."""
    system = platform.system().lower()
    home = Path.home()
    
    if system == "darwin":  # macOS
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "linux":
        return home / ".config" / "claude" / "claude_desktop_config.json"
    elif system == "windows":
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:
        # Fallback Linux
        return home / ".config" / "claude" / "claude_desktop_config.json"


def detect_project_dirs() -> dict[str, str]:
    """Tenta detectar automaticamente os diretórios dos projetos."""
    home = Path.home()
    projects = {
        "KPL": None,
        "OnclickERP": None,
        "apiecomm": None,
    }
    
    # Tenta encontrar em ~/KPL, ~/OnclickERP, ~/apiecomm
    for name in projects:
        default_path = home / name
        if default_path.exists():
            projects[name] = str(default_path)
    
    return projects


def main() -> int:
    """Função principal de instalação."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║     🔗 Hermes Bridge — Instalador Automático                 ║
║     Conecta Claude Code ao Hermes Agent                     ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    total_steps = 8
    
    # ═══════════════════════════════════════════════════════════
    # PASSO 1: Verificar sistema operacional
    # ═══════════════════════════════════════════════════════════
    print_step(1, total_steps, "Verificando sistema operacional")
    
    system = platform.system()
    print(f"   Sistema detectado: {system}")
    
    if system not in ("Linux", "Darwin", "Windows"):
        print(f"   ⚠️  Sistema '{system}' não testado. Continuando mesmo assim...")
    
    # ═══════════════════════════════════════════════════════════
    # PASSO 2: Verificar Python
    # ═══════════════════════════════════════════════════════════
    print_step(2, total_steps, "Verificando Python")
    
    py_version = sys.version_info
    print(f"   Python: {py_version.major}.{py_version.minor}.{py_version.micro}")
    
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 12):
        print("   ❌ ERRO: Python 3.12+ é necessário.")
        print(f"   Versão atual: {py_version.major}.{py_version.minor}")
        print("   Por favor, instale Python 3.12+ antes de continuar.")
        return 1
    
    print("   ✅ Python OK")
    
    # ═══════════════════════════════════════════════════════════
    # PASSO 3: Verificar Git
    # ═══════════════════════════════════════════════════════════
    print_step(3, total_steps, "Verificando Git")
    
    git_result = run(["git", "--version"])
    if git_result.returncode != 0:
        print("   ❌ ERRO: Git não encontrado.")
        print("   Por favor, instale o Git antes de continuar.")
        return 1
    
    git_version = git_result.stdout.strip()
    print(f"   ✅ Git encontrado: {git_version}")
    
    # ═══════════════════════════════════════════════════════════
    # PASSO 4: Verificar/instalar Hermes
    # ═══════════════════════════════════════════════════════════
    print_step(4, total_steps, "Verificando Hermes Agent")
    
    hermes_path = find_hermes()
    hermes_dir = ""
    
    if hermes_path:
        print(f"   ✅ Hermes encontrado: {hermes_path}")
        hermes_dir = str(Path(hermes_path).parent)
    else:
        print("   ❌ Hermes NÃO encontrado no PATH.")
        print("   " + "-"*50)
        print("   O Hermes Bridge precisa que o Hermes Agent esteja instalado")
        print("   e acessível nesta máquina.")
        print("   " + "-"*50)
        
        if ask_yes_no("Você quer continuar mesmo assim?", default=False):
            hermes_dir = ask(
                "Digite o diretório onde o hermes está instalado (ex: /home/user/.local/bin)",
                default=str(Path.home() / ".local" / "bin")
            )
        else:
            print("\n   🛑 Instalação cancelada.")
            print("   Instale o Hermes primeiro: https://hermes-agent.nousresearch.com/docs/")
            return 1
    
    # ═══════════════════════════════════════════════════════════
    # PASSO 5: Perguntar diretórios dos projetos
    # ═══════════════════════════════════════════════════════════
    print_step(5, total_steps, "Configurando diretórios dos projetos")
    
    print("   O Hermes precisa acessar os códigos fonte localmente.")
    print("   Vou tentar detectar automaticamente...")
    
    detected = detect_project_dirs()
    project_dirs: dict[str, str] = {}
    
    for name, default_path in detected.items():
        if default_path:
            print(f"   ✅ {name}: encontrado em {default_path}")
            if ask_yes_no(f"   Confirmar {name} neste caminho?", default=True):
                project_dirs[name] = default_path
            else:
                custom = ask(f"   Digite o caminho correto para {name}", default="")
                if custom:
                    project_dirs[name] = custom
        else:
            print(f"   ❓ {name}: NÃO encontrado automaticamente")
            custom = ask(f"   Digite o caminho para {name} (ou deixe em branco se não tiver)", default="")
            if custom:
                project_dirs[name] = custom
    
    # ═══════════════════════════════════════════════════════════
    # PASSO 6: Clonar repositório e criar virtualenv
    # ═══════════════════════════════════════════════════════════
    print_step(6, total_steps, "Instalando dependências")
    
    repo_url = "https://github.com/calligioni/hermes-bridge.git"
    install_dir = Path.home() / "hermes-bridge"
    
    if install_dir.exists():
        print(f"   ⚠️  Diretório {install_dir} já existe.")
        if ask_yes_no("   Deseja remover e clonar novamente?", default=False):
            shutil.rmtree(install_dir)
        else:
            print("   Usando diretório existente.")
    
    if not install_dir.exists():
        print(f"   📥 Clonando repositório...")
        clone_result = run(["git", "clone", repo_url, str(install_dir)])
        if clone_result.returncode != 0:
            print(f"   ❌ ERRO ao clonar: {clone_result.stderr}")
            return 1
        print("   ✅ Repositório clonado")
    
    venv_dir = install_dir / ".venv"
    if venv_dir.exists():
        print(f"   ⚠️  Virtualenv já existe em {venv_dir}")
        if ask_yes_no("   Deseja recriar?", default=False):
            shutil.rmtree(venv_dir)
    
    if not venv_dir.exists():
        print(f"   🐍 Criando virtualenv...")
        venv_result = run([sys.executable, "-m", "venv", str(venv_dir)])
        if venv_result.returncode != 0:
            print(f"   ❌ ERRO ao criar virtualenv: {venv_result.stderr}")
            return 1
        print("   ✅ Virtualenv criado")
    
    # Determina o caminho do Python no venv
    if platform.system() == "Windows":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"
    
    print(f"   📦 Instalando dependências...")
    pip_result = run([str(venv_python), "-m", "pip", "install", "-r", str(install_dir / "requirements.txt")])
    if pip_result.returncode != 0:
        print(f"   ❌ ERRO ao instalar dependências: {pip_result.stderr}")
        return 1
    print("   ✅ Dependências instaladas")
    
    # ═══════════════════════════════════════════════════════════
    # PASSO 7: Configurar Claude Code
    # ═══════════════════════════════════════════════════════════
    print_step(7, total_steps, "Configurando Claude Code MCP")
    
    config_path = get_claude_config_path()
    print(f"   Arquivo de configuração: {config_path}")
    
    # Monta o PATH para o ambiente
    path_env = os.environ.get("PATH", "")
    if hermes_dir and hermes_dir not in path_env.split(":"):
        # Adiciona o diretório do hermes ao PATH
        path_env = f"{hermes_dir}:{path_env}"
    
    # Monta a configuração MCP
    server_config = {
        "mcpServers": {
            "hermes-bridge": {
                "command": str(venv_python),
                "args": [str(install_dir / "server.py")],
                "env": {
                    "HERMES_BIN": "hermes",
                    "HERMES_MAX_TURNS": "20",
                    "PATH": path_env,
                }
            }
        }
    }
    
    # Lê configuração existente ou cria nova
    existing_config: dict = {}
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                existing_config = json.load(f)
            print("   📄 Configuração existente encontrada, mesclando...")
        except json.JSONDecodeError:
            print("   ⚠️  Configuração existente corrompida, criando nova...")
            existing_config = {}
    
    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}
    
    existing_config["mcpServers"]["hermes-bridge"] = server_config["mcpServers"]["hermes-bridge"]
    
    # Cria os diretórios se não existirem
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Salva a configuração
    with open(config_path, "w") as f:
        json.dump(existing_config, f, indent=2)
    
    print(f"   ✅ Configuração salva em: {config_path}")
    
    # ═══════════════════════════════════════════════════════════
    # PASSO 8: Testar
    # ═══════════════════════════════════════════════════════════
    print_step(8, total_steps, "Testando instalação")
    
    print("   🧪 Testando server.py...")
    test_result = run([str(venv_python), str(install_dir / "test_server.py")], timeout=60)
    
    if test_result.returncode == 0:
        print("   ✅ Teste passou!")
    else:
        print("   ⚠️  Teste falhou (isso pode ser normal se o Hermes não estiver configurado)")
        print(f"   Saída: {test_result.stdout[:500]}")
        print(f"   Erro: {test_result.stderr[:500]}")
    
    # ═══════════════════════════════════════════════════════════
    # RESUMO
    # ═══════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("🎉 INSTALAÇÃO CONCLUÍDA!")
    print("="*60)
    print()
    print("📁 Diretório de instalação:", install_dir)
    print("🐍 Python do virtualenv:", venv_python)
    print("⚙️  Configuração Claude:", config_path)
    print()
    print("📋 Próximos passos:")
    print("   1. REINICIE o Claude Code (feche e abra novamente)")
    print("   2. No chat, digite: Pergunta pro Hermes qual é o banco do KPL")
    print()
    print("📁 Projetos configurados:")
    for name, path in project_dirs.items():
        print(f"   • {name}: {path}")
    
    print()
    print("❓ Se tiver problemas:")
    print("   • Verifique se o Hermes está instalado: hermes --help")
    print("   • Verifique se o PATH inclui o diretório do hermes")
    print("   • Veja o troubleshooting no README.md")
    print()
    print("🔗 Repositório: https://github.com/calligioni/hermes-bridge")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Instalação cancelada pelo usuário.")
        sys.exit(130)
