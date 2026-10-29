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
| Resposta mantém contexto da conversa | ❌ | ✅ Histórico persistente |

O **Hermes** tem acesso a:
- Código fonte de todos os projetos (KPL, OnclickERP, APIECOMM)
- Graphify (grafo de conhecimento do código)
- Skills especializadas (SQL, Delphi, .NET)
- Memória persistente entre sessões

---

## 🚀 Instalação Rápida (máquina do time que usa Claude Code)

### 1. Clone ou copie este diretório

```bash
# Na máquina que roda Claude Code (mesma rede do Hermes)
cd ~
git clone <repo> claude-hermes-bridge
# ou copie a pasta /home/onclick/claude-hermes-bridge
```

### 2. Crie o virtualenv e instale dependências

```bash
cd ~/claude-hermes-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure o Claude Code

Adicione ao arquivo de configuração MCP do Claude Code:

**Caminho do arquivo:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Conteúdo:**

```json
{
  "mcpServers": {
    "hermes-bridge": {
      "command": "/home/SEU_USUARIO/claude-hermes-bridge/.venv/bin/python",
      "args": ["/home/SEU_USUARIO/claude-hermes-bridge/server.py"],
      "env": {
        "HERMES_BIN": "hermes",
        "HERMES_MAX_TURNS": "20",
        "PATH": "/usr/local/bin:/usr/bin:/bin:/home/SEU_USUARIO/.local/bin"
      }
    }
  }
}
```

> **⚠️ IMPORTANTE:**
> - Substitua `SEU_USUARIO` pelo nome de usuário real da máquina
> - O `PATH` precisa incluir o diretório onde o `hermes` está instalado (ex: `/home/onclick/.local/bin`)
> - A máquina que roda Claude Code precisa ter o Hermes instalado e acessível via PATH

### 4. Teste

Reinicie o Claude Code e digite:

```
Pergunta pro Hermes: qual é o banco de dados principal do KPL?
```

O Claude vai detectar a tool `ask_hermes` e usar automaticamente. A resposta do Hermes aparece no chat.

---

## 🛠️ Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `HERMES_BIN` | `hermes` | Caminho para o binário do Hermes |
| `HERMES_MAX_TURNS` | `20` | Máximo de iterações do Hermes por pergunta |
| `PATH` | — | **OBRIGATÓRIO** — precisa incluir o diretório do `hermes` |

---

## 📖 Como usar no Claude Code

### Perguntas simples
```
Pergunta pro Hermes qual é a procedure que atualiza status de pedido no KPL.
```

### Com contexto adicional
```
Pergunta pro Hermes: onde fica a tabela de configurações de frete?
Contexto: estou trabalhando no módulo de expedição do KPL.
```

### Especificando o projeto
```
Pergunta pro Hermes sobre a estrutura de menus do BackOffice.
Diretório: /home/onclick/OnclickERP
```

### Limpando o histórico
```
Limpa o histórico do Hermes.
```
O Claude vai chamar `clear_hermes_history` automaticamente.

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

## 🧪 Teste standalone (sem o Claude)

Para validar que o server está funcionando antes de configurar no Claude:

```bash
cd ~/claude-hermes-bridge
source .venv/bin/activate
python test_server.py
```

---

## 🔧 Troubleshooting

### "hermes: command not found"
- O `PATH` no `claude_desktop_config.json` não inclui o diretório do `hermes`
- Verifique: `which hermes` no terminal → adicione esse diretório ao `PATH`

### "Timeout" ou resposta vazia
- A máquina do Hermes pode estar sobrecarregada
- Reduza `HERMES_MAX_TURNS` para `10`
- Verifique se a máquina está na mesma rede

### "Erro ao inicializar MCP server"
- Verifique se o Python 3.12+ está instalado: `python3 --version`
- Verifique se o virtualenv foi criado corretamente
- Verifique se o Claude Code suporta MCP (versão recente)

### O Claude não chama a tool automaticamente
- O Claude Code nem sempre sabe que deve usar a tool. Seja explícito: **"Use a tool ask_hermes para perguntar..."**
- Ou pergunte: **"Pergunta pro Hermes: ..."**

---

## 📁 Estrutura do projeto

```
claude-hermes-bridge/
├── server.py           # MCP Server principal
├── test_server.py      # Script de teste standalone
├── requirements.txt    # Dependências Python
└── README.md           # Este arquivo
```

---

## 📝 Notas Técnicas

- O MCP server roda como **stdio** (entrada/saída padrão), iniciado automaticamente pelo Claude Code
- Não precisa de servidor web ou porta aberta — comunicação é local via pipes
- O histórico fica **apenas em memória** — se o processo do MCP server morrer, o histórico é perdido
- Para histórico persistente entre reinícios, seria necessário salvar em arquivo (não implementado por padrão)
- Cada instância do server é isolada — duas sessões do Claude Code não compartilham histórico

---

## 🤝 Suporte

Problemas? Verifique:
1. `hermes doctor` — saúde do Hermes
2. `python test_server.py` — teste standalone
3. Logs do Claude Code em `~/.config/claude/logs/`
