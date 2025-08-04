# Guia de Deploy - API MyMetric

Este guia irá ajudá-lo a fazer o deploy da API MyMetric em um servidor na nuvem usando Docker.

## 📋 Pré-requisitos

- Servidor Linux (Ubuntu 20.04+ recomendado)
- Docker e Docker Compose instalados
- Domínio configurado: `api.mymetric.app`
- Acesso SSH ao servidor

## 🚀 Passos para Deploy

### 1. Preparar o Servidor

```bash
# Atualizar o sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER
```

### 2. Configurar o Projeto

```bash
# Clonar o projeto (ou fazer upload dos arquivos)
git clone <seu-repositorio>
cd api

# Criar arquivo .env
cp env.example .env
nano .env
```

### 3. Configurar Variáveis de Ambiente

Edite o arquivo `.env`:

```env
# Configurações da API
SECRET_KEY=sua_chave_secreta_muito_segura_aqui_use_openssl_rand_hex_32

# Configurações do Google Cloud/BigQuery
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account-key.json

# Configurações do servidor
HOST=0.0.0.0
PORT=8000
```

### 4. Configurar Credenciais

```bash
# Criar diretório de credenciais
mkdir -p credentials

# Adicionar arquivo de credenciais do Google Cloud
# Faça upload do arquivo service-account-key.json para credentials/
```

### 5. Configurar SSL (Opcional para Produção)

#### Opção A: Let's Encrypt (Recomendado)

```bash
# Instalar Certbot
sudo apt install certbot

# Obter certificado
sudo certbot certonly --standalone -d api.mymetric.app

# Copiar certificados
sudo cp /etc/letsencrypt/live/api.mymetric.app/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/api.mymetric.app/privkey.pem nginx/ssl/key.pem

# Configurar renovação automática
sudo crontab -e
# Adicionar linha: 0 12 * * * /usr/bin/certbot renew --quiet && cp /etc/letsencrypt/live/api.mymetric.app/fullchain.pem /path/to/your/project/nginx/ssl/cert.pem && cp /etc/letsencrypt/live/api.mymetric.app/privkey.pem /path/to/your/project/nginx/ssl/key.pem && docker-compose -f /path/to/your/project/docker-compose.prod.yml restart nginx
```

#### Opção B: Certificado Auto-assinado (Desenvolvimento)

```bash
# Gerar certificado auto-assinado
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/key.pem \
    -out nginx/ssl/cert.pem \
    -subj "/C=BR/ST=State/L=City/O=Organization/CN=api.mymetric.app"
```

### 6. Fazer Deploy

```bash
# Tornar o script executável
chmod +x deploy.sh

# Executar deploy
./deploy.sh production
```

### 7. Verificar Deploy

```bash
# Verificar status dos containers
docker-compose -f docker-compose.prod.yml ps

# Verificar logs
docker-compose -f docker-compose.prod.yml logs -f

# Testar API
curl https://api.mymetric.app/
```

## 🔧 Configurações Adicionais

### Firewall

```bash
# Configurar UFW
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### Monitoramento

```bash
# Instalar htop para monitoramento
sudo apt install htop

# Verificar uso de recursos
htop
```

### Logs

```bash
# Ver logs da API
docker-compose -f docker-compose.prod.yml logs -f api

# Ver logs do Nginx
docker-compose -f docker-compose.prod.yml logs -f nginx
```

## 🚨 Troubleshooting

### Problemas Comuns

1. **Porta 80/443 já em uso**
   ```bash
   sudo netstat -tulpn | grep :80
   sudo systemctl stop apache2  # se necessário
   ```

2. **Erro de permissão no Docker**
   ```bash
   sudo chmod 666 /var/run/docker.sock
   # Ou fazer logout/login após adicionar usuário ao grupo docker
   ```

3. **Certificado SSL não encontrado**
   ```bash
   # Verificar se os arquivos existem
   ls -la nginx/ssl/
   ```

4. **API não responde**
   ```bash
   # Verificar logs
   docker-compose -f docker-compose.prod.yml logs api
   
   # Verificar se o container está rodando
   docker-compose -f docker-compose.prod.yml ps
   ```

### Comandos Úteis

```bash
# Reiniciar serviços
docker-compose -f docker-compose.prod.yml restart

# Parar todos os serviços
docker-compose -f docker-compose.prod.yml down

# Reconstruir imagens
docker-compose -f docker-compose.prod.yml build --no-cache

# Limpar recursos não utilizados
docker system prune -a
```

## 📊 Monitoramento e Manutenção

### Backup

```bash
# Backup das configurações
tar -czf backup-$(date +%Y%m%d).tar.gz .env credentials/ nginx/ssl/

# Backup do banco (se aplicável)
# Implementar conforme necessário
```

### Atualizações

```bash
# Atualizar código
git pull origin main

# Reconstruir e redeployar
./deploy.sh production
```

## 🔒 Segurança

- Mantenha o sistema atualizado
- Use senhas fortes
- Configure firewall adequadamente
- Monitore logs regularmente
- Faça backups regulares
- Use HTTPS em produção

## 📞 Suporte

Para problemas específicos, verifique:
1. Logs dos containers
2. Configuração do DNS
3. Configuração do firewall
4. Certificados SSL
5. Variáveis de ambiente 