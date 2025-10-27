#!/bin/bash

# Script de Configuração do Servidor
# Execute este script como root ou com sudo

set -e

echo "🔧 Configurando servidor para deploy da API MyMetric..."

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Este script deve ser executado como root ou com sudo"
    exit 1
fi

# Atualizar sistema
echo "📦 Atualizando sistema..."
apt update && apt upgrade -y

# Instalar dependências básicas
echo "📦 Instalando dependências..."
apt install -y \
    curl \
    wget \
    git \
    htop \
    ufw \
    certbot \
    python3-certbot-nginx \
    unzip

# Instalar Docker
echo "🐳 Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo "✅ Docker já está instalado"
fi

# Instalar Docker Compose
echo "🐳 Instalando Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    echo "✅ Docker Compose já está instalado"
fi

# Adicionar usuário ao grupo docker
echo "👤 Configurando permissões do Docker..."
if id "$SUDO_USER" &>/dev/null; then
    usermod -aG docker "$SUDO_USER"
    echo "✅ Usuário $SUDO_USER adicionado ao grupo docker"
else
    echo "⚠️  Não foi possível adicionar usuário ao grupo docker"
fi

# Configurar firewall
echo "🔥 Configurando firewall..."
ufw --force enable
ufw allow ssh
ufw allow 80
ufw allow 443
echo "✅ Firewall configurado"

# Configurar timezone (opcional)
echo "⏰ Configurando timezone..."
timedatectl set-timezone America/Sao_Paulo

# Configurar swap (se necessário)
echo "💾 Verificando memória swap..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "✅ Swap configurado (2GB)"
else
    echo "✅ Swap já configurado"
fi

# Configurar limites do sistema
echo "⚙️  Configurando limites do sistema..."
cat >> /etc/security/limits.conf << EOF
* soft nofile 65536
* hard nofile 65536
* soft nproc 32768
* hard nproc 32768
EOF

# Configurar sysctl para melhor performance
echo "⚙️  Configurando parâmetros do kernel..."
cat >> /etc/sysctl.conf << EOF
# Network settings
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_tw_buckets = 2000000
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_tw_recycle = 0

# File system settings
fs.file-max = 2097152
EOF

# Aplicar configurações do sysctl
sysctl -p

echo ""
echo "✅ Configuração do servidor concluída!"
echo ""
echo "📋 Próximos passos:"
echo "1. Faça logout e login novamente para aplicar as permissões do Docker"
echo "2. Clone ou faça upload do projeto para o servidor"
echo "3. Configure o arquivo .env com suas variáveis de ambiente"
echo "4. Adicione o arquivo de credenciais do Google Cloud em credentials/"
echo "5. Execute o script de deploy: ./deploy.sh production"
echo ""
echo "🔗 Documentação completa: DEPLOY_GUIDE.md" 