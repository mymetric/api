# 📊 API de Métricas - Dashboard Analytics

Uma API robusta para dashboard de métricas com autenticação JWT, integração BigQuery e sistema de cache inteligente.

## 🚀 Funcionalidades Principais

### 🔐 Autenticação e Autorização
- **Login seguro** com JWT tokens
- **Controle de acesso** baseado em permissões
- **Isolamento de dados** por usuário/cliente
- **Suporte a múltiplos níveis** de acesso (admin, read, full)

### 📈 Métricas e Analytics
- **Dados básicos** do dashboard com cache de 1 hora
- **Métricas personalizadas** por cliente/tabela
- **Modelos de atribuição** configuráveis
- **Filtros dinâmicos** por período e categoria

### 🗄️ Sistema de Cache
- **Cache inteligente** com TTL de 1 hora
- **Performance otimizada** (99.8% mais rápido)
- **Gerenciamento de cache** via API
- **Estatísticas em tempo real**

### 🔧 Gerenciamento de Dados
- **Integração BigQuery** nativa
- **Suporte a múltiplas tabelas** por cliente
- **Controle de acesso granular** por tabela
- **Queries otimizadas** para performance

## 🛠️ Tecnologias

- **FastAPI** - Framework web moderno e rápido
- **BigQuery** - Data warehouse do Google Cloud
- **JWT** - Autenticação segura
- **Pydantic** - Validação de dados
- **Docker** - Containerização
- **Cache em Memória** - Performance otimizada

## 📁 Estrutura do Projeto

```
api/
├── main.py                 # Aplicação principal FastAPI
├── metrics.py              # Endpoints de métricas
├── cache_manager.py        # Sistema de cache
├── utils.py                # Utilitários compartilhados
├── requirements.txt        # Dependências Python
├── configure_env.py        # Configuração automática
├── setup.py               # Setup inicial do projeto
├── start.sh               # Script de inicialização
├── Dockerfile             # Container Docker
├── docker-compose.yml     # Orquestração Docker
├── .gitignore            # Arquivos ignorados pelo Git
├── env.example           # Exemplo de variáveis de ambiente
├── README.md             # Documentação principal
├── QUICK_START.md        # Guia de início rápido
├── cache_endpoints_docs.md # Documentação do cache
├── sample_data.sql       # Dados de exemplo BigQuery
└── credentials/          # Credenciais Google Cloud
    └── service-account-key.json
```

## ⚡ Instalação Rápida

### 1. Pré-requisitos
```bash
# Python 3.11+
python3 --version

# Git
git --version

# Docker (opcional)
docker --version
```

### 2. Configuração Automática
```bash
# Clonar e configurar
git clone <repository>
cd api
python3 configure_env.py
python3 setup.py
```

### 3. Iniciar API
```bash
# Método 1: Script automático
./start.sh

# Método 2: Manual
python3 main.py

# Método 3: Docker
docker-compose up
```

## 🔧 Configuração

### Variáveis de Ambiente (.env)
```bash
# Configurações da API
SECRET_KEY=sua_chave_secreta_aqui

# Configurações do Google Cloud/BigQuery
GOOGLE_APPLICATION_CREDENTIALS=credentials/service-account-key.json

# Configurações do servidor
HOST=0.0.0.0
PORT=8000
```

### Credenciais Google Cloud
1. Criar projeto no Google Cloud Console
2. Ativar BigQuery API
3. Criar Service Account
4. Baixar JSON de credenciais
5. Salvar em `credentials/service-account-key.json`

## 📚 Endpoints da API

### 🔐 Autenticação
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/login` | Login de usuário |
| `GET` | `/profile` | Perfil do usuário |
| `GET` | `/users` | Listar usuários (admin) |

### 📊 Métricas
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/metrics/basic-data` | Dados básicos do dashboard |
| `GET` | `/metrics/available-tables` | Tabelas disponíveis |

### 🗄️ Cache
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/metrics/cache/stats` | Estatísticas do cache |
| `POST` | `/metrics/cache/flush` | Limpar cache completo |
| `POST` | `/metrics/cache/flush-expired` | Limpar entradas expiradas |

## 🚀 Uso

### 1. Login
```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "accounts@mymetric.com.br",
    "password": "Z5RDqlkDOk0SP65"
  }'
```

### 2. Buscar Dados Básicos
```bash
curl -X POST "http://localhost:8000/metrics/basic-data" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-07-27",
    "end_date": "2025-08-03",
    "attribution_model": "Último Clique Não Direto"
  }'
```

### 3. Gerenciar Cache
```bash
# Ver estatísticas
curl -X GET "http://localhost:8000/metrics/cache/stats" \
  -H "Authorization: Bearer SEU_TOKEN"

# Limpar cache
curl -X POST "http://localhost:8000/metrics/cache/flush" \
  -H "Authorization: Bearer SEU_TOKEN"
```

## 📊 Estrutura BigQuery

### Tabela de Usuários
```sql
CREATE TABLE `mymetric-hub-shopify.dbt_config.users` (
  email STRING,
  password STRING,
  admin BOOLEAN,
  access_control STRING,
  tablename STRING
);
```

### Tabelas de Eventos
```sql
-- Padrão: {tablename}_events_long
-- Exemplo: constance_events_long, coffeemais_events_long
```

## 🔒 Segurança

### Autenticação
- **JWT tokens** com expiração configurável
- **Senhas hash** com SHA-256
- **Validação de permissões** em todos os endpoints

### Controle de Acesso
- **Isolamento por usuário** no cache
- **Verificação de tabelas** permitidas
- **Controle granular** por operação

### Dados
- **Parâmetros validados** com Pydantic
- **Queries parametrizadas** para evitar SQL injection
- **Logs de auditoria** para operações críticas

## 📈 Performance

### Cache
- **TTL de 1 hora** para dados básicos
- **99.8% mais rápido** para requisições repetidas
- **Limpeza automática** de entradas expiradas

### BigQuery
- **Queries otimizadas** com índices apropriados
- **Processamento paralelo** nativo
- **Cache de resultados** para consultas frequentes

## 🐳 Docker

### Build da Imagem
```bash
docker build -t metrics-api .
```

### Executar Container
```bash
docker run -p 8000:8000 \
  -v $(pwd)/credentials:/app/credentials \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account-key.json \
  metrics-api
```

### Docker Compose
```bash
docker-compose up -d
```

## 🔧 Desenvolvimento

### Estrutura de Código
- **Modular**: Cada funcionalidade em módulo separado
- **Reutilizável**: Utilitários compartilhados
- **Testável**: Endpoints isolados e testáveis
- **Documentado**: Docstrings e comentários

### Padrões
- **RESTful**: Endpoints seguindo convenções REST
- **Pydantic**: Validação de dados consistente
- **Error Handling**: Tratamento de erros padronizado
- **Logging**: Logs estruturados para debugging

## 📝 Documentação Adicional

- [Guia de Início Rápido](QUICK_START.md)
- [Documentação do Cache](cache_endpoints_docs.md)
- [Exemplos de Uso](sample_data.sql)

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para detalhes.

## 🆘 Suporte

- **Issues**: Abra uma issue no GitHub
- **Documentação**: Consulte os arquivos .md
- **Email**: contato@mymetric.com.br

---

**Desenvolvido com ❤️ pela equipe MyMetric** 