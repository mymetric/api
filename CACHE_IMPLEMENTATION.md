# Implementação de Cache - Daily Metrics e Orders

## Resumo das Mudanças

Implementei cache com TTL de 1 hora para os endpoints `daily_metrics` e `orders` no arquivo `metrics.py`.

## Endpoints com Cache Implementado

### 1. `/metrics/daily-metrics` (Funil de Conversão)
- **Cache**: `daily_metrics_cache`
- **TTL**: 1 hora
- **Parâmetros de cache**:
  - `email`: Email do usuário
  - `start_date`: Data de início
  - `end_date`: Data de fim
  - `table_name`: Nome da tabela (opcional)

### 2. `/metrics/orders` (Orders Detalhados)
- **Cache**: `orders_cache`
- **TTL**: 1 hora
- **Parâmetros de cache**:
  - `email`: Email do usuário
  - `start_date`: Data de início
  - `end_date`: Data de fim
  - `table_name`: Nome da tabela (opcional)
  - `limit`: Limite de resultados
  - `offset`: Offset para paginação
  - `traffic_category`: Categoria de tráfego (opcional)
  - `fs_traffic_category`: Categoria de tráfego primeiro clique (opcional)
  - `fsm_traffic_category`: Categoria de tráfego primeiro lead (opcional)

## Arquivos Modificados

### 1. `cache_manager.py`
- Adicionadas instâncias de cache:
  ```python
  daily_metrics_cache = CacheManager(ttl_hours=1)
  orders_cache = CacheManager(ttl_hours=1)
  ```

### 2. `metrics.py`
- Importação dos novos caches
- Implementação de cache nos endpoints `daily_metrics` e `orders`
- Atualização dos endpoints de gerenciamento de cache:
  - `/cache/flush`: Limpa todos os caches
  - `/cache/flush-expired`: Remove entradas expiradas de todos os caches
  - `/cache/stats`: Estatísticas de todos os caches

## Funcionamento do Cache

### Verificação de Cache
1. Gera chave única baseada nos parâmetros da requisição
2. Verifica se existe no cache e se não expirou
3. Se encontrado, retorna dados do cache com flag `source: 'cache'`

### Armazenamento no Cache
1. Após consulta ao BigQuery, prepara dados para cache
2. Armazena no cache com timestamp
3. Retorna dados com flag `source: 'database'`

### Informações de Cache na Resposta
```json
{
  "cache_info": {
    "source": "cache|database",
    "cached_at": "2024-01-15T10:30:00",
    "ttl_hours": 1
  }
}
```

## Benefícios

1. **Performance**: Reduz consultas ao BigQuery
2. **Custo**: Diminui custos de processamento
3. **Velocidade**: Respostas mais rápidas para consultas repetidas
4. **Escalabilidade**: Melhora capacidade de lidar com múltiplas requisições

## Endpoints de Gerenciamento

### Limpar Todos os Caches
```http
POST /metrics/cache/flush
```

### Remover Entradas Expiradas
```http
POST /metrics/cache/flush-expired
```

### Ver Estatísticas
```http
GET /metrics/cache/stats
```

## Status Atual dos Endpoints

| Endpoint | Cache | TTL |
|----------|-------|-----|
| `/basic-data` | ✅ | 1 hora |
| `/daily-metrics` | ✅ | 1 hora |
| `/orders` | ✅ | 1 hora |
| `/traffic-categories` | ❌ | - |
| `/dashboard` | ❌ | - |
| `/revenue` | ❌ | - |
| `/orders` (GET) | ❌ | - |
| `/customers` | ❌ | - |
| `/available-tables` | ❌ | - |

## Próximos Passos

Considerar implementar cache nos demais endpoints conforme necessidade de performance e padrão de uso. 