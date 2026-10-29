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

## ⚠️ Antes de começar — perguntas importantes

Antes de instalar, verifique se você responde **SIM** a todas estas perguntas:

### 1. A máquina que roda Claude Code está na mesma rede que a máquina do Hermes?
- [ ] Sim, estão na mesma rede local / VPN / rede interna
- [ ] Não → **NÃO** vai funcionar. O Hermes Bridge precisa conseguir executar o comando `hermes` localmente.

> **Exemplo:** Se o Hermes roda em `192.168.1.50` e seu Claude Code está em `192.168.1.30`, OK. Se o Hermes é remoto (AWS, outra rede), você precisa de outra solução (fale com o time de infra).

### 2. O Hermes está instalado e funcionando nesta máquina?
- [ ] Sim, consigo rodar `hermes --help` no terminal
- [ ] Não → Instale o Hermes primeiro: https://hermes-agent.nousresearch.com/docs/

### 3. Qual é o caminho do diretório HOME do usuário nesta máquina?
- [ ] Linux/macOS: `/home/SEU_USUARIO` (ex: `/home/joao`, `/Users/maria`)
- [ ] Windows: `C:\Users\SEU_USUARIO`

> Você precisa saber isso para configurar os caminhos no `claude_desktop_config.json`.

### 4. O Python 3.12+ está instalado?
- [ ] Sim: `python3 --version` retorna 3.12 ou superior
- [ ] Não → Instale Python 3.12+ primeiro

### 5. O Git está instalado?
- [ ] Sim: `git --version` funciona no terminal
- [ ] Não → Instale o Git primeiro

### 6. Você tem permissão para criar pastas em `$HOME`?
- [ ] Sim
- [ ] Não → Peça permissão ao administrador

### 7. Qual é o seu sistema operacional?
- [ ] Linux
- [ ] macOS
- [ ] Windows

> Cada SO tem caminhos diferentes para o arquivo de configuração do Claude.

### 8. Os projetos (KPL, OnclickERP, APIECOMM) estão clonados nesta máquina?
- [ ] Sim, em `/home/SEU_USUARIO/KPL`, `/home/SEU_USUARIO/OnclickERP`, `/home/SEU_USUARIO/apiecomm`
- [ ] Não → O Hermes precisa acessar os códigos fonte localmente

---

## 🚀 Instalação Completa (passo a passo)

### Passo 1: Clone o repositório

Abra um terminal na máquina onde roda o Claude Code e execute:

```bash
cd ~
git clone https://github.com/calligioni/hermes-bridge.git
# OU, se preferir outro nome de pasta:
git clone https://github.com/calligioni/hermes-bridge.git claude-hermes-bridge
```

**Verifique se funcionou:**
```bash
ls ~/hermes-bridge  # ou ~/claude-hermes-bridge
# Deve mostrar: server.py, test_server.py, requirements.txt, README.md
```

> **⚠️ IMPORTANTE:** Se você mudou o nome da pasta na hora do clone, lembre-se de usar o novo nome em todos os comandos abaixo.

---

### Passo 2: Descubra o caminho do Python na sua máquina

```bash
which python3
# Exemplo de resposta: /usr/bin/python3
```

Guarde esse caminho — você vai precisar dele no Passo 5.

---

### Passo 3: Crie o virtualenv e instale dependências

```bash
cd ~/hermes-bridge  # ou ~/claude-hermes-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Verifique se funcionou:**
```bash
ls .venv/bin/python
# Deve mostrar o caminho do Python no virtualenv
```

**Caminho que você vai usar no Passo 5:**
- Se clonou como `hermes-bridge`: `~/hermes-bridge/.venv/bin/python`
- Se clonou como `claude-hermes-bridge`: `~/claude-hermes-bridge/.venv/bin/python`

---

### Passo 4: Descubra onde está o binário `hermes`

```bash
which hermes
# Exemplo de resposta: /home/onclick/.local/bin/hermes
```

**Descubra o diretório:**
```bash
dirname $(which hermes)
# Exemplo de resposta: /home/onclick/.local/bin
```

Guarde esse diretório — você precisa incluir ele no `PATH` do Passo 5.

> **Se `which hermes` não retornar nada:** O Hermes não está no PATH. Descubra onde ele está instalado (talvez em `~/.local/bin/hermes` ou `/usr/local/bin/hermes`).

---

### Passo 5: Configure o Claude Code

Agora você precisa editar o arquivo de configuração MCP do Claude Code.

#### Encontre o arquivo de configuração no seu sistema:

| Sistema Operacional | Caminho do arquivo |
|---------------------|-------------------|
| **Linux** | `~/.config/claude/claude_desktop_config.json` |
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |

#### Crie ou edite o arquivo:

Se o arquivo **não existir**, crie ele. Se já existir, **adicione** a seção `hermes-bridge` dentro de `mcpServers`.

**Conteúdo completo (se o arquivo não existir):**

```json
{
  "mcpServers": {
    "hermes-bridge": {
      "command": "CAMINHO_DO_PYTHON_NO_VENV",
      "args": ["CAMINHO_DO_SERVER_PY"],
      "env": {
        "HERMES_BIN": "hermes",
        "HERMES_MAX_TURNS": "20",
        "PATH": "SEU_PATH_ATUAL:DIRETORIO_DO_HERMES"
      }
    }
  }
}
```

**Substitua os valores (exemplo real para Linux):**

```json
{
  "mcpServers": {
    "hermes-bridge": {
      "command": "/home/joao/hermes-bridge/.venv/bin/python",
      "args": ["/home/joao/hermes-bridge/server.py"],
      "env": {
        "HERMES_BIN": "hermes",
        "HERMES_MAX_TURNS": "20",
        "PATH": "/usr/local/bin:/usr/bin:/bin:/home/joao/.local/bin"
      }
    }
  }
}
```

**Substitua os valores (exemplo real para macOS):**

```json
{
  "mcpServers": {
    "hermes-bridge": {
      "command": "/Users/maria/hermes-bridge/.venv/bin/python",
      "args": ["/Users/maria/hermes-bridge/server.py"],
      "env": {
        "HERMES_BIN": "hermes",
        "HERMES_MAX_TURNS": "20",
        "PATH": "/usr/local/bin:/usr/bin:/bin:/Users/maria/.local/bin"
      }
    }
  }
}
```

**Substitua os valores (exemplo real para Windows):**

```json
{
  "mcpServers": {
    "hermes-bridge": {
      "command": "C:\\Users\\joao\\hermes-bridge\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\joao\\hermes-bridge\\server.py"],
      "env": {
        "HERMES_BIN": "hermes",
        "HERMES_MAX_TURNS": "20",
        "PATH": "C:\\Users\\joao\\.local\\bin;C:\\Windows\\System32"
      }
    }
  }
}
```

> **⚠️ ATENÇÃO:** Substitua `joao`/`maria` pelo seu nome de usuário REAL. O PATH precisa incluir o diretório onde o `hermes` está instalado.

---

### Passo 6: Reinicie o Claude Code

Feche completamente o Claude Code (Ctrl+Q / Cmd+Q) e abra novamente.

O Claude Code vai detectar automaticamente o MCP Server na inicialização.

---

### Passo 7: Teste!

No chat do Claude Code, digite:

```
Pergunta pro Hermes: qual é o banco de dados principal do KPL?
```

O Claude deve:
1. Detectar que existe uma tool `ask_hermes`
2. Chamar a tool com a sua pergunta
3. Mostrar a resposta do Hermes no chat

**Se o Claude não chamar automaticamente**, seja mais explícito:
```
Use a tool ask_hermes para perguntar: qual é o banco de dados principal do KPL?
```

---

## 📖 Exemplos de uso no Claude Code

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
cd ~/hermes-bridge  # ou ~/claude-hermes-bridge
source .venv/bin/activate
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
2. Se não retornar nada, procure: `find /home -name "hermes" -type f 2>/dev/null`
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

### Resposta vem com "session_id:" ou texto estranho
**Isso é normal** em alguns casos — o server.py já filtra isso, mas se persistir, atualize o repositório para a versão mais recente.

---

## 📁 Estrutura do projeto

```
hermes-bridge/
├── .gitignore              # Ignora .venv, __pycache__, etc.
├── server.py               # MCP Server principal (o Claude inicia isso)
├── test_server.py          # Script de teste standalone
├── requirements.txt        # Dependências Python (só mcp>=2.0.0)
└── README.md               # Este arquivo
```

---

## 📝 Notas Técnicas

- O MCP server roda como **stdio** (entrada/saída padrão), iniciado automaticamente pelo Claude Code
- Não precisa de servidor web ou porta aberta — comunicação é local via pipes
- O histórico fica **apenas em memória** — se o processo do MCP server morrer, o histórico é perdido
- Cada instância do server é isolada — duas sessões do Claude Code não compartilham histórico

---

## 🤝 Precisa de ajuda?

Se nenhuma das soluções de troubleshooting funcionar:

1. Rode o teste standalone: `python test_server.py`
2. Verifique a saúde do Hermes: `hermes doctor`
3. Verifique os logs do Claude Code em `~/.config/claude/logs/`
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

Depois reinicie o Claude Code.
