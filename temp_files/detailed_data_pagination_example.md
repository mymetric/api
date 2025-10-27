# Detailed Data - Paginação e Cache Otimizado

## Melhorias Implementadas

### 1. **Cache Aumentado para 4 Horas**
- TTL aumentado de 1 hora para 4 horas
- Melhor performance para consultas repetidas

### 2. **Paginação Completa**
- `limit`: Número máximo de registros (padrão: 1000, máximo: 5000)
- `offset`: Número de registros para pular (padrão: 0)
- `order_by`: Campo para ordenação (padrão: "Pedidos")

### 3. **Campos de Ordenação Válidos**
- `Pedidos` (padrão)
- `Receita`
- `Sessoes`
- `Adicoes_ao_Carrinho`
- `Data`
- `Hora`

## Exemplos de Uso

### 1. **Consulta Básica (Primeira Página)**
```bash
curl -X POST "http://localhost:8000/metrics/detailed-data" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "table_name": "constance",
    "attribution_model": "purchase",
    "limit": 1000,
    "offset": 0,
    "order_by": "Pedidos"
  }'
```

### 2. **Segunda Página**
```bash
curl -X POST "http://localhost:8000/metrics/detailed-data" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "table_name": "constance",
    "limit": 1000,
    "offset": 1000,
    "order_by": "Receita"
  }'
```

### 3. **Ordenar por Receita (Top Performers)**
```bash
curl -X POST "http://localhost:8000/metrics/detailed-data" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "table_name": "constance",
    "limit": 500,
    "offset": 0,
    "order_by": "Receita"
  }'
```

### 4. **Usar Last-Request com Paginação**
```bash
curl -X GET "http://localhost:8000/metrics/last-request/detailed-data?table_name=constance" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Response com Paginação

```json
{
  "data": [...],
  "total_rows": 1000,
  "summary": {
    "total_revenue": 150000.0,
    "total_orders": 500,
    "total_sessions": 10000,
    "total_add_to_cart": 2000,
    "conversion_rate": 5.0,
    "add_to_cart_rate": 20.0,
    "table_name": "constance",
    "project_name": "mymetric-hub-shopify",
    "attribution_model": "purchase"
  },
  "cache_info": {
    "source": "database",
    "cached_at": "2024-01-15T10:30:00",
    "ttl_hours": 4
  },
  "pagination": {
    "limit": 1000,
    "offset": 0,
    "order_by": "Pedidos",
    "has_more": true
  }
}
```

## Benefícios da Paginação

### 1. **Performance Melhorada**
- Consultas mais rápidas com menos dados
- Menor uso de memória
- Resposta mais rápida para o usuário

### 2. **Cache Mais Eficiente**
- Cache de 4 horas reduz consultas ao banco
- Cache específico por parâmetros de paginação
- Melhor reutilização de dados

### 3. **Flexibilidade**
- Ordenação personalizada
- Controle sobre quantidade de dados
- Navegação por páginas

## Validações Implementadas

### 1. **Limites de Paginação**
- `limit`: Máximo 5000 registros
- `offset`: Não pode ser negativo
- Valores inválidos são corrigidos automaticamente

### 2. **Campos de Ordenação**
- Apenas campos válidos são aceitos
- Campo inválido reverte para "Pedidos"

### 3. **Cache Inteligente**
- Cache específico por combinação de parâmetros
- TTL de 4 horas para melhor performance
- Informações de cache no response

## Dicas de Uso

### 1. **Para Dashboards**
- Use `limit: 100` para carregamento rápido
- Ordene por `Receita` ou `Pedidos` para métricas principais

### 2. **Para Relatórios Detalhados**
- Use `limit: 5000` para dados completos
- Implemente paginação no frontend

### 3. **Para Consultas Frequentes**
- Use o endpoint `last-request` para reutilizar consultas
- Aproveite o cache de 4 horas

### 4. **Monitoramento**
- Verifique `has_more` para implementar paginação
- Use `cache_info` para otimizar consultas 