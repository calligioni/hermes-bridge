#!/bin/bash
# Script para criar o repositório no GitHub e fazer o push
# Execute na máquina local após criar o repo no GitHub

set -e

echo "🔗 Configurando push para GitHub..."
echo ""
echo "⚠️  ANTES DE RODAR ESTE SCRIPT:"
echo "   1. Crie um repositório VAZIO no GitHub: https://github.com/new"
echo "   2. Nome do repositório: hermes-bridge"
echo "   3. NÃO inicialize com README (já temos um)"
echo "   4. Copie o URL do repositório (ex: https://github.com/calligioni/hermes-bridge.git)"
echo ""

REPO_URL="${1:-}"

if [ -z "$REPO_URL" ]; then
    echo "❌ Uso: $0 https://github.com/SEU_USUARIO/hermes-bridge.git"
    echo ""
    echo "   Exemplo:"
    echo "   $0 https://github.com/calligioni/hermes-bridge.git"
    exit 1
fi

echo "📡 Adicionando remote: $REPO_URL"
git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"

echo "🚀 Fazendo push..."
git branch -M master
git push -u origin master

echo ""
echo "✅ Push concluído!"
echo ""
echo "📎 Seu repositório está em: $REPO_URL"
echo ""
echo "🔗 Próximo passo: compartilhe este link com o time para eles instalarem."
