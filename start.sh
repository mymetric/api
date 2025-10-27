#!/bin/bash

# Script de inicialização da API Dashboard de Métricas

echo "🚀 Iniciando API Dashboard de Métricas..."

# Verificar se o Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não está instalado!"
    exit 1
fi

# Verificar se o arquivo .env existe
if [ ! -f ".env" ]; then
    echo "⚠️  Arquivo .env não encontrado!"
    echo "📝 Executando configuração inicial..."
    python3 setup.py
fi

# Verificar se as dependências estão instaladas
echo "🔍 Verificando dependências..."
python3 -c "import fastapi, uvicorn, google.cloud.bigquery" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Instalando dependências..."
    pip3 install -r requirements.txt
fi

# Verificar se as credenciais do Google Cloud estão configuradas
if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ ! -f "credentials/service-account-key.json" ]; then
    echo "⚠️  Credenciais do Google Cloud não encontradas!"
    echo "📋 Configure o arquivo .env com o caminho correto para as credenciais"
    echo "💡 Exemplo: GOOGLE_APPLICATION_CREDENTIALS=credentials/service-account-key.json"
fi

# Iniciar a API
echo "🌟 Iniciando servidor..."
echo "📡 API estará disponível em: http://localhost:8000"
echo "📖 Documentação: http://localhost:8000/docs"
echo ""
echo "Pressione Ctrl+C para parar o servidor"
echo ""

python3 main.py 