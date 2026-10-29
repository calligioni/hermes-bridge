# 🔗 Hermes Bridge — MCP Server para Claude Code (Cliente Remoto)

Conecta o **Claude Code** (na máquina local do time) ao **Hermes Agent** (na máquina remota 10.250.240.206), permitindo que o time faça perguntas ao Hermes e receba respostas no chat do Claude — **com histórico de conversa persistente**.

---

## 🏗️ Arquitetura

```
┌─────────────────────┐      HTTP POST       ┌──────────────────────────┐
│  MÁQUINA DO TIME    │  ─────────────────▶  │  MÁQUINA REMOTA          │
│  (Mac/Windows/Linux)│     pergunta →       │  (10.250.240.206)        │
│                     │     resposta         │  Hermes + Código Fonte   │
│  Claude Code ──▶    │                      │  KPL / OnclickERP /      │
│  server.py (MCP)    │  ◀──────────────────  │  APIECOMM                │
│  (cliente HTTP)     │                      │  remote_hermes_api.py   │
└─────────────────────┘                      └──────────────────────────┘
```

**O Hermes NÃO roda na máquina do time.** O Hermes roda apenas na máquina remota (10.250.240.206), que tem acesso ao código fonte. O time se conecta via HTTP.

---

## 📋 O que isso faz

| Cenário | Sem o Bridge | Com o Bridge |
|---------|-------------|--------------|
| Time usa Claude Code para editar código | ✅ | ✅ |
| Precisa saber onde está uma procedure no KPL | ❌ (Claude não tem acesso ao graphify) | ✅ Pergunta pro Hermes |
| Precisa entender relacionamentos entre tabelas | ❌ | ✅ Pergunta pro Hermes |
| Precisa de análise profunda do OnclickERP | ❌ | ✅ Pergunta pro Hermes |
| Precisa de ajuda com integração APIECOMM | ❌ | ✅ Pergunta pro Hermes |
| Resposta mantém contexto da conversa | ❌ | ✅ Histórico persistente |

O **Hermes** (na máquina remota) tem acesso a:
- Código fonte de todos os projetos (KPL, OnclickERP, APIECOMM)
- Graphify (grafo de conhecimento do código)
- Skills especializadas (SQL, Delphi, .NET, React)
- Memória persistente entre sessões

---

## 🚀 Instalação Automática (RECOMENDADO)

A forma mais fácil: o **Claude Code** faz tudo sozinho.

### No chat do Claude Code, diga:

> **"Instala pra mim o repositório https://github.com/calligioni/hermes-bridge.git"**

O Claude vai:
1. **Ler** o repositório e encontrar o `install.py`
2. **Executar** o script de instalação
3. **Perguntar** o que precisar (IP remoto, confirmações)
4. **Configurar** o `claude_desktop_config.json`
5. **Informar** quando estiver pronto

### Ou, se quiser modo automático (sem perguntas):

> **"Roda o install.py do repo https://github.com/calligioni/hermes-bridge.git com --yes --remote-ip 10.250.240.206"**

O script vai assumir os defaults e não fazer perguntas.

---

## 🛠️ Instalação Manual

### Na MÁQUINA REMOTA (10.250.240.206) — onde o Hermes está

1. Clone o repositório:
```bash
cd ~
git clone https://github.com/calligioni/hermes-bridge.git
```

2. Inicie o servidor HTTP:
```bash
cd ~/hermes-bridge
python3 remote_hermes_api.py
```

O servidor vai escutar em `0.0.0.0:8655` e aceitar conexões de qualquer máquina da rede.

3. Para rodar em background (opcional):
```bash
nohup python3 remote_hermes_api.py > /tmp/hermes_api.log 2>&1 &
```

### Na MÁQUINA DO TIME (Mac/Windows/Linux) — onde roda Claude Code

1. Clone o repositório:
```bash
cd ~
git clone https://github.com/calligioni/hermes-bridge.git
```

2. Rode o instalador:
```bash
cd hermes-bridge
python3 install.py
```

O instalador vai:
- Detectar seu SO (Linux/macOS/Windows)
- Perguntar o IP da máquina remota (padrão: 10.250.240.206)
- Criar virtualenv
- Instalar dependências (`mcp>=2.0.0`)
- Configurar o `claude_desktop_config.json`
- Testar a conexão com o servidor remoto

Ou modo automático:
```bash
python3 install.py --yes --remote-ip 10.250.240.206
```

3. Reinicie o Claude Code.

---

## 📖 Como usar no Claude Code

### Perguntas simples (KPL)
```
Pergunta pro Hermes qual é a procedure que atualiza status de pedido no KPL.
```

### Com contexto adicional
```
Pergunta pro Hermes: onde fica a tabela de configurações de frete?
Contexto: estou trabalhando no módulo de expedição do KPL.
```

### Especificando o projeto (OnclickERP)
```
Pergunta pro Hermes sobre a estrutura de menus do BackOffice.
Diretório: /home/onclick/OnclickERP
```

### Perguntando sobre APIECOMM
```
Pergunta pro Hermes: qual é o endpoint que sincroniza produtos com a plataforma?
Diretório: /home/onclick/apiecomm
```

### Pergunta com histórico (contexto mantido)
```
Pergunta pro Hermes: e como essa tabela se relaciona com a de pedidos?
```
> O Hermes vai lembrar que você estava falando sobre a tabela de configurações de frete.

### Limpando o histórico
```
Limpa o histórico do Hermes.
```

---

## 🧠 Como funciona o histórico

O Hermes Bridge mantém um **histórico de conversa em memória** (limitado às últimas 10 interações = 20 mensagens). Isso significa:

1. **Primeira pergunta:** "Qual o banco do KPL?"
2. **Segunda pergunta:** "E qual a tabela principal de pedidos?"
   - O Hermes recebe: histórico + pergunta nova
   - Entende que "a tabela principal de pedidos" é no contexto do KPL
3. **Terceira pergunta:** "Como ela se relaciona com expedição?"
   - O Hermes sabe que "ela" = "tabela de pedidos" do KPL

O histórico é **por sessão do Claude** — se o Claude Code reiniciar, o histórico zera.

---

## 🛠️ Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `HERMES_API_URL` | `http://10.250.240.206:8655` | URL do servidor remoto onde o Hermes roda |
| `HERMES_MAX_TURNS` | `20` | Máximo de iterações do Hermes por pergunta (no servidor) |

---

## 🔧 Troubleshooting

### "Não consegui conectar ao servidor remoto"
**Causa:** O servidor remoto (`remote_hermes_api.py`) não está rodando na máquina 10.250.240.206.

**Solução:**
1. SSH para a máquina remota: `ssh usuario@10.250.240.206`
2. Verifique se o servidor está rodando:
   ```bash
   curl http://localhost:8655/health
   ```
3. Se não responder, inicie o servidor:
   ```bash
   cd ~/hermes-bridge
   python3 remote_hermes_api.py
   ```

### "hermes: command not found" (no servidor remoto)
**Causa:** O Hermes não está instalado ou não está no PATH da máquina remota.

**Solução:** Instale o Hermes na máquina remota: https://hermes-agent.nousresearch.com/docs/

### "Timeout" ou resposta vazia
**Causas:**
- A máquina remota está sobrecarregada
- A pergunta é muito complexa
- Problemas de rede entre as máquinas

**Soluções:**
- Verifique conectividade: `ping 10.250.240.206`
- Teste a porta: `curl http://10.250.240.206:8655/health`

### O Claude não chama a tool automaticamente
**Solução:** Seja mais explícito no prompt:
```
Use a tool ask_hermes para perguntar: [sua pergunta aqui]
```

### macOS: "python3: command not found"
**Solução:** Instale Python 3.12+ via Homebrew:
```bash
brew install python@3.12
```

### macOS: "git: command not found"
**Solução:** Instale o Xcode Command Line Tools:
```bash
xcode-select --install
```

---

## 📁 Estrutura do projeto

```
hermes-bridge/
├── remote_hermes_api.py    # ⭐ Servidor HTTP (roda na máquina remota 10.250.240.206)
├── server.py               # MCP Server cliente (roda na máquina do time, conecta via HTTP)
├── install.py              # Script de instalação automática (roda na máquina do time)
├── test_server.py          # Teste standalone
├── requirements.txt        # Dependências Python (mcp>=2.0.0)
├── push-to-github.sh       # Script auxiliar para push
├── .gitignore              # Ignora .venv, __pycache__, etc.
└── README.md               # Este arquivo
```

---

## 📝 Notas Técnicas

- **Máquina remota (10.250.240.206):** Roda `remote_hermes_api.py` — um servidor HTTP simples que recebe perguntas via POST e delega ao Hermes local.
- **Máquina do time:** Roda `server.py` como MCP Server do Claude Code — é um cliente HTTP que se conecta ao servidor remoto.
- **Comunicação:** HTTP POST entre as máquinas. Porta padrão: 8655.
- **Segurança:** O servidor escuta em `0.0.0.0` (todas as interfaces). Certifique-se de que a rede interna é segura.
- **O histórico fica apenas em memória** — se o processo do MCP server morrer, o histórico é perdido.

---

## 🤝 Precisa de ajuda?

Se nenhuma das soluções de troubleshooting funcionar:

1. Teste o servidor remoto: `curl http://10.250.240.206:8655/health`
2. Verifique a saúde do Hermes na máquina remota: `hermes doctor`
3. Verifique os logs do Claude Code:
   - **macOS:** `~/Library/Application Support/Claude/logs/`
   - **Linux:** `~/.config/claude/logs/`
   - **Windows:** `%APPDATA%\Claude\logs\`
4. Abra uma issue no repositório: https://github.com/calligioni/hermes-bridge/issues

---

## 🔄 Atualizando

### Na máquina do time:
```bash
cd ~/hermes-bridge
git pull
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Na máquina remota:
```bash
cd ~/hermes-bridge
git pull
# Reinicie o remote_hermes_api.py
```

Depois reinicie o Claude Code na máquina do time.

---

## 🏗️ Compatibilidade

| Componente | Linux | macOS | Windows |
|-----------|-------|-------|---------|
| `remote_hermes_api.py` (servidor) | ✅ | ✅ | ✅ |
| `server.py` (cliente MCP) | ✅ | ✅ | ✅ |
| `install.py` (instalador) | ✅ | ✅ | ✅ |

**Requisitos mínimos:**
- Python 3.12+
- Git
- Rede entre as máquinas (mesma rede ou VPN)

---

## 📄 Licença

MIT License — veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 🔗 Links

- Repositório: https://github.com/calligioni/hermes-bridge
- Hermes Agent: https://hermes-agent.nousresearch.com/docs/
