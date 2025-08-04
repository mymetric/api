#!/bin/bash

# Script para gerar chave secreta segura
# Execute este script para gerar uma SECRET_KEY segura para o arquivo .env

echo "🔐 Gerando chave secreta segura..."

# Gerar chave secreta usando OpenSSL
SECRET_KEY=$(openssl rand -hex 32)

echo "✅ Chave secreta gerada com sucesso!"
echo ""
echo "📋 Adicione a seguinte linha ao seu arquivo .env:"
echo ""
echo "SECRET_KEY=$SECRET_KEY"
echo ""
echo "⚠️  IMPORTANTE:"
echo "- Mantenha esta chave em segurança"
echo "- Não compartilhe ou commite no repositório"
echo "- Use uma chave diferente para cada ambiente"
echo ""
echo "🔗 Para criar o arquivo .env completo:"
echo "cp env.example .env"
echo "nano .env" 