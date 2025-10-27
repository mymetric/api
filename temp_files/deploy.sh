#!/bin/bash

# Script de Deploy para API MyMetric
# Uso: ./deploy.sh [production|staging]

set -e

ENVIRONMENT=${1:-production}
DOMAIN="api.mymetric.app"

echo "🚀 Iniciando deploy para $ENVIRONMENT..."

# Verificar se o Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker não está rodando. Por favor, inicie o Docker e tente novamente."
    exit 1
fi

# Verificar se as credenciais existem
if [ ! -f "credentials/service-account-key.json" ]; then
    echo "❌ Arquivo de credenciais não encontrado em credentials/service-account-key.json"
    echo "Por favor, adicione o arquivo de credenciais do Google Cloud."
    exit 1
fi

# Verificar se o arquivo .env existe
if [ ! -f ".env" ]; then
    echo "❌ Arquivo .env não encontrado"
    echo "Por favor, crie o arquivo .env baseado no env.example"
    exit 1
fi

# Verificar se os certificados SSL existem (para produção)
if [ "$ENVIRONMENT" = "production" ]; then
    if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/key.pem" ]; then
        echo "⚠️  Certificados SSL não encontrados em nginx/ssl/"
        echo "Para produção, você precisa adicionar os certificados SSL:"
        echo "  - nginx/ssl/cert.pem"
        echo "  - nginx/ssl/key.pem"
        echo ""
        echo "Você pode usar Let's Encrypt ou outro provedor de certificados."
        echo "Deseja continuar sem SSL? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

echo "📦 Construindo imagens Docker..."
docker-compose -f docker-compose.prod.yml build

echo "🔄 Parando containers existentes..."
docker-compose -f docker-compose.prod.yml down

echo "🚀 Iniciando containers..."
docker-compose -f docker-compose.prod.yml up -d

echo "⏳ Aguardando containers iniciarem..."
sleep 10

# Verificar se os containers estão rodando
echo "🔍 Verificando status dos containers..."
docker-compose -f docker-compose.prod.yml ps

# Verificar logs
echo "📋 Últimos logs da API:"
docker-compose -f docker-compose.prod.yml logs --tail=20 api

echo "✅ Deploy concluído!"
echo ""
echo "🌐 Sua API está disponível em:"
if [ "$ENVIRONMENT" = "production" ]; then
    echo "   https://$DOMAIN"
else
    echo "   http://localhost:8000"
fi
echo ""
echo "📊 Para verificar os logs:"
echo "   docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🛑 Para parar os serviços:"
echo "   docker-compose -f docker-compose.prod.yml down" 