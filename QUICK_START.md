# ⚡ Guia de Início Rápido - API Dashboard de Métricas

Este guia te ajudará a configurar e executar a API de métricas em menos de 5 minutos!

## 🎯 O que você vai conseguir

- ✅ API funcionando com autenticação JWT
- ✅ Integração com Google BigQuery
- ✅ Endpoints de métricas prontos para uso
- ✅ Documentação interativa
- ✅ Containerização com Docker

## 📋 Pré-requisitos

- **Python 3.11+** instalado
- **Conta Google Cloud** com BigQuery habilitado
- **Credenciais de Service Account** do Google Cloud
- **Git** (opcional, para clonar o repositório)

## 🚀 Configuração em 5 Passos

### Passo 1: Preparar o Ambiente

```bash
# Verificar Python
python3 --version

# Criar diretório do projeto (se necessário)
mkdir api-dashboard && cd api-dashboard

# Ou clonar o repositório
git clone <repository-url> && cd api
```

### Passo 2: Configurar Credenciais

1. **Acesse o Google Cloud Console**: https://console.cloud.google.com/
2. **Crie um Service Account** ou use um existente
3. **Baixe o arquivo JSON** de credenciais
4. **Crie a pasta credentials** e coloque o arquivo lá:

```bash
mkdir credentials
# Coloque seu service-account-key.json aqui
```

### Passo 3: Configurar Variáveis de Ambiente

```bash
# Executar script de configuração automática
python3 configure_env.py

# Ou criar manualmente
cp env.example .env
# Edite o arquivo .env com suas configurações
```

### Passo 4: Instalar Dependências

```bash
# Instalar todas as dependências
pip install -r requirements.txt

# Ou instalar manualmente
pip install fastapi uvicorn google-cloud-bigquery google-auth pydantic python-jose passlib python-multipart python-dotenv
```

### Passo 5: Iniciar a API

```bash
# Método 1: Python direto
python3 main_fixed.py

# Método 2: Script de inicialização
./start.sh

# Método 3: Docker
docker-compose up -d
```

## 🎉 Sucesso! API Funcionando

A API estará disponível em: **http://localhost:8000**

### Verificar se está funcionando:

```bash
curl -X GET "http://localhost:8000/"
```

**Resposta esperada:**
```json
{
  "message": "API Dashboard de Métricas - Funcionando!"
}
```

## 📚 Documentação Interativa

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔐 Primeiro Login

### Usuários de Exemplo

A API vem com usuários de exemplo configurados:

#### Administrador
- **Email**: `admin@exemplo.com`
- **Senha**: `123`
- **Acesso**: Completo (admin)

#### Usuário Normal
- **Email**: `usuario@exemplo.com`
- **Senha**: `123`
- **Acesso**: Leitura

### Fazer Login

```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@exemplo.com",
    "password": "123"
  }'
```

**Resposta esperada:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## 🔌 Testando os Endpoints

### 1. Health Check
```bash
curl -X GET "http://localhost:8000/"
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@exemplo.com", "password": "123"}'
```

### 3. Perfil do Usuário (com token)
```bash
# Substitua SEU_TOKEN pelo token recebido no login
curl -X GET "http://localhost:8000/profile" \
  -H "Authorization: Bearer SEU_TOKEN"
```

### 4. Listar Usuários (apenas admin)
```bash
curl -X GET "http://localhost:8000/users" \
  -H "Authorization: Bearer SEU_TOKEN"
```

### 5. Métricas (com token)
```bash
# Receita total
curl -X GET "http://localhost:8000/metrics/revenue" \
  -H "Authorization: Bearer SEU_TOKEN"

# Total de pedidos
curl -X GET "http://localhost:8000/metrics/orders" \
  -H "Authorization: Bearer SEU_TOKEN"
```

## 🐳 Usando Docker

### Opção 1: Docker Compose (Recomendado)

```bash
# Construir e iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar
docker-compose down
```

### Opção 2: Docker Direto

```bash
# Construir imagem
docker build -t metrics-api .

# Executar container
docker run -p 8000:8000 --env-file .env metrics-api
```

## 🗄️ Configuração do BigQuery

### Estrutura Esperada

A API espera as seguintes tabelas no BigQuery:

```sql
-- Tabela de usuários
CREATE TABLE `mymetric-hub-shopify.dbt_config.users` (
    email STRING,
    admin BOOLEAN,
    access_control STRING,
    tablename STRING,
    password STRING
);

-- Inserir usuários de exemplo
INSERT INTO `mymetric-hub-shopify.dbt_config.users`
(email, admin, access_control, tablename, password)
VALUES
('admin@exemplo.com', true, 'full', 'admin_metrics', 'MTIz'),
('usuario@exemplo.com', false, 'read', 'user_metrics', 'MTIz');
```

### Executar SQL de Exemplo

```bash
# Usar o arquivo sample_data.sql
# Execute as queries no BigQuery Console ou via bq CLI
```

## 🔧 Configurações Avançadas

### Variáveis de Ambiente

```env
# Configurações da API
SECRET_KEY=sua_chave_secreta_muito_segura_para_jwt_tokens

# Configurações do Google Cloud/BigQuery
GOOGLE_APPLICATION_CREDENTIALS=credentials/service-account-key.json

# Configurações do servidor
HOST=0.0.0.0
PORT=8000
```

### Personalizar Configurações

- **Porta**: Altere `PORT` no arquivo `.env`
- **Host**: Altere `HOST` para `127.0.0.1` para acesso local apenas
- **Secret Key**: Gere uma nova chave secreta para produção

## 🚨 Solução de Problemas

### Erro: "address already in use"
```bash
# Parar processos na porta 8000
lsof -ti:8000 | xargs kill -9

# Ou usar porta diferente
PORT=8001 python3 main_fixed.py
```

### Erro: "credentials not found"
```bash
# Verificar se o arquivo existe
ls -la credentials/service-account-key.json

# Verificar permissões
chmod 600 credentials/service-account-key.json
```

### Erro: "BigQuery connection failed"
```bash
# Verificar credenciais
python3 -c "from google.cloud import bigquery; print('BigQuery OK')"

# Verificar projeto
gcloud config get-value project
```

### Erro: "Module not found"
```bash
# Reinstalar dependências
pip install -r requirements.txt --force-reinstall
```

## 📱 Integração com Frontend

### Exemplo com JavaScript

```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'admin@exemplo.com',
    password: '123'
  })
});

const { access_token } = await loginResponse.json();

// Usar token para requisições
const profileResponse = await fetch('http://localhost:8000/profile', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
```

### Exemplo com Python

```python
import requests

# Login
login_data = {
    "email": "admin@exemplo.com",
    "password": "123"
}

response = requests.post("http://localhost:8000/login", json=login_data)
token = response.json()["access_token"]

# Usar token
headers = {"Authorization": f"Bearer {token}"}
profile = requests.get("http://localhost:8000/profile", headers=headers)
```

## 🎯 Próximos Passos

1. **Explorar a documentação**: http://localhost:8000/docs
2. **Testar todos os endpoints** com diferentes usuários
3. **Configurar dados reais** no BigQuery
4. **Integrar com seu frontend**
5. **Configurar para produção**

## 🆘 Precisa de Ajuda?

- **Documentação completa**: [README.md](README.md)
- **Issues**: Abra uma issue no GitHub
- **Email**: seu-email@exemplo.com

---

**🚀 Sua API está pronta para uso!** 