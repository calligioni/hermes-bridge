# 🔗 Hermes Bridge — MCP Server para Claude Code

Conecta o **Claude Code** (ou Claude Desktop) ao **Hermes Agent**, permitindo que o time que usa Claude faça perguntas ao Hermes e receba respostas no mesmo chat — **com histórico de conversa persistente** entre chamadas.

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

O **Hermes** tem acesso a:
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
3. **Perguntar** o que precisar (diretórios dos projetos, confirmações)
4. **Configurar** o `claude_desktop_config.json`
5. **Informar** quando estiver pronto

### Ou, se quiser modo automático (sem perguntas):

> **"Roda o install.py do repo https://github.com/calligioni/hermes-bridge.git com --yes"**

O script vai assumir os defaults e não fazer perguntas.

---

## 🛠️ Instalação Manual

Se preferir fazer na mão, siga os passos abaixo.

### Pré-requisitos

Antes de começar, confirme que tem:

- [ ] **Python 3.12+** instalado (`python3 --version`)
- [ ] **Git** instalado (`git --version`)
- [ ] **Hermes Agent** instalado e funcionando (`hermes --help`)
- [ ] A máquina está na mesma rede que o Hermes
- [ ] Os projetos (KPL, OnclickERP, APIECOMM) clonados localmente (opcional, mas recomendado)

### Passo a passo

```bash
# 1. Clone o repositório
cd ~
git clone https://github.com/calligioni/hermes-bridge.git

# 2. Rode o instalador interativo
cd hermes-bridge
python3 install.py

# Ou, modo automático (sem perguntas):
python3 install.py --yes

# Ou, força reinstalação completa:
python3 install.py --force
```

O instalador vai:
- Detectar seu SO (Linux/macOS/Windows)
- Criar virtualenv em `~/.venv`
- Instalar dependências (`mcp>=2.0.0`)
- Perguntar os diretórios dos projetos
- Configurar o `claude_desktop_config.json`
- Testar a conexão

Depois, **reinicie o Claude Code**.

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
| `HERMES_BIN` | `hermes` | Caminho para o binário do Hermes |
| `HERMES_MAX_TURNS` | `20` | Máximo de iterações do Hermes por pergunta |
| `PATH` | — | **OBRIGATÓRIO** — precisa incluir o diretório do `hermes` |

---

## 🧪 Teste standalone (sem o Claude Code)

Para validar que o server está funcionando antes de configurar no Claude:

```bash
cd ~/hermes-bridge
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows
python test_server.py
```

Se tudo estiver OK, você verá:
- ✅ Resposta do initialize
- ✅ Lista de tools (`ask_hermes`, `clear_hermes_history`)
- ✅ Resposta do Hermes à pergunta de teste

---

## 🔧 Troubleshooting

### "hermes: command not found"
**Causa:** O `PATH` no `claude_desktop_config.json` não inclui o diretório do `hermes`.

**Solução:**
1. Descubra onde está o hermes: `which hermes`
2. Se não retornar nada, procure: `find ~ -name "hermes" -type f 2>/dev/null`
3. Adicione o diretório ao PATH no JSON de configuração

### "Timeout" ou resposta vazia
**Causas:**
- A máquina do Hermes está sobrecarregada
- A pergunta é muito complexa

**Soluções:**
- Reduza `HERMES_MAX_TURNS` para `10` no JSON de configuração
- Faça perguntas mais específicas
- Verifique se a máquina tem recursos suficientes

### "Erro ao inicializar MCP server"
**Causas:**
- Python não está instalado ou é versão antiga (< 3.12)
- Virtualenv não foi criado corretamente
- Dependências não foram instaladas

**Soluções:**
```bash
cd ~/hermes-bridge
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### O Claude não chama a tool automaticamente
**Solução:** Seja mais explícito no prompt:
```
Use a tool ask_hermes para perguntar: [sua pergunta aqui]
```

### "ModuleNotFoundError: No module named 'mcp'"
**Causa:** O virtualenv não foi ativado ou as dependências não foram instaladas.

**Solução:**
```bash
cd ~/hermes-bridge
source .venv/bin/activate
pip install mcp
```

### macOS: "python3: command not found"
**Solução:** O macOS não vem com Python 3.12+ por padrão. Instale via Homebrew:
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
├── .gitignore              # Ignora .venv, __pycache__, etc.
├── install.py              # ⭐ Script de instalação automática
├── server.py               # MCP Server principal (o Claude inicia isso)
├── test_server.py          # Teste standalone
├── requirements.txt        # Dependências Python (só mcp>=2.0.0)
└── README.md               # Este arquivo
```

---

## 📝 Notas Técnicas

- O MCP server roda como **stdio** (entrada/saída padrão), iniciado automaticamente pelo Claude Code
- Não precisa de servidor web ou porta aberta — comunicação é local via pipes
- O histórico fica **apenas em memória** — se o processo do MCP server morrer, o histórico é perdido
- Cada instância do server é isolada — duas sessões do Claude Code não compartilham histórico
- O `install.py` é **idempotente** — pode rodar de novo que ele atualiza o que precisa

---

## 🤝 Precisa de ajuda?

Se nenhuma das soluções de troubleshooting funcionar:

1. Rode o teste standalone: `python test_server.py`
2. Verifique a saúde do Hermes: `hermes doctor`
3. Verifique os logs do Claude Code:
   - **macOS:** `~/Library/Application Support/Claude/logs/`
   - **Linux:** `~/.config/claude/logs/`
   - **Windows:** `%APPDATA%\Claude\logs\`
4. Abra uma issue no repositório: https://github.com/calligioni/hermes-bridge/issues

---

## 🔄 Atualizando

Para atualizar para a versão mais recente:

```bash
cd ~/hermes-bridge
git pull
source .venv/bin/activate
pip install -r requirements.txt
```

Ou simplesmente rode o `install.py` de novo — ele faz `git pull` automaticamente.

Depois reinicie o Claude Code.

---

## 🏗️ Compatibilidade

| Sistema | Status | Notas |
|---------|--------|-------|
| Linux | ✅ Testado | Caminho config: `~/.config/claude/` |
| macOS | ✅ Suportado | Caminho config: `~/Library/Application Support/Claude/` |
| Windows | ✅ Suportado | Caminho config: `%APPDATA%\Claude\` |

**Requisitos mínimos:**
- Python 3.12+
- Git
- Hermes Agent instalado

---

## 📄 Licença

MIT License — veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 🔗 Links

- Repositório: https://github.com/calligioni/hermes-bridge
- Hermes Agent: https://hermes-agent.nousresearch.com/docs/
