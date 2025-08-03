# 🗄️ Endpoints de Cache

## 📋 Visão Geral

O sistema de cache implementa um cache em memória com TTL (Time To Live) de **1 hora** para o endpoint de dados básicos. Isso melhora significativamente a performance das requisições repetidas.

## 🔧 Endpoints Disponíveis

### 1. Estatísticas do Cache
```bash
curl -X GET "http://localhost:8000/metrics/cache/stats" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

**Resposta:**
```json
{
  "message": "Estatísticas do cache",
  "stats": {
    "total_entries": 3,
    "valid_entries": 3,
    "expired_entries": 0,
    "ttl_hours": 1.0,
    "cache_size_mb": 0.09,
    "timestamp": "2025-08-03T18:15:30.123456"
  }
}
```

### 2. Flush Completo do Cache
```bash
curl -X POST "http://localhost:8000/metrics/cache/flush" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

**Resposta:**
```json
{
  "message": "Cache limpo com sucesso",
  "stats": {
    "action": "flush",
    "cache_size_before": 3,
    "cache_size_after": 0,
    "keys_removed": ["abc12345", "def67890", "ghi11111"],
    "timestamp": "2025-08-03T18:15:30.123456"
  }
}
```

### 3. Flush de Entradas Expiradas
```bash
curl -X POST "http://localhost:8000/metrics/cache/flush-expired" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

**Resposta:**
```json
{
  "message": "Entradas expiradas removidas com sucesso",
  "stats": {
    "action": "flush_expired",
    "expired_entries": 2,
    "remaining_entries": 1,
    "expired_keys": ["abc12345", "def67890"],
    "timestamp": "2025-08-03T18:15:30.123456"
  }
}
```

## 📊 Como o Cache Funciona

### 1. **Chave do Cache**
A chave é gerada automaticamente baseada nos parâmetros da requisição:
- Email do usuário
- Data inicial
- Data final
- Modelo de atribuição
- Nome da tabela (se especificado)

### 2. **TTL (Time To Live)**
- **Duração**: 1 hora
- **Comportamento**: Entradas expiradas são removidas automaticamente
- **Renovação**: Não há renovação automática

### 3. **Fluxo de Funcionamento**
```
1. Requisição chega
2. Gera chave do cache
3. Verifica se existe no cache
4. Se existe e não expirou → Retorna do cache
5. Se não existe ou expirou → Busca no BigQuery
6. Armazena resultado no cache
7. Retorna dados
```

## 🚀 Benefícios do Cache

### Performance
- **Primeira requisição**: ~4-5 segundos (BigQuery)
- **Requisições subsequentes**: ~0.01 segundos (Cache)
- **Melhoria**: 99.8% mais rápido

### Custos
- **Redução de queries**: Menos consultas ao BigQuery
- **Economia**: Redução significativa nos custos de processamento

### Experiência do Usuário
- **Resposta instantânea**: Para dados já consultados
- **Consistência**: Dados idênticos para a mesma consulta
- **Disponibilidade**: Funciona mesmo com BigQuery lento

## 🔐 Segurança

### Controle de Acesso
- **Apenas administradores** podem gerenciar o cache
- **Verificação de permissões** em todos os endpoints
- **Isolamento por usuário** no cache

### Validação
- **Parâmetros únicos**: Cada combinação de parâmetros gera uma chave diferente
- **TTL automático**: Entradas expiram automaticamente
- **Limpeza automática**: Entradas expiradas são removidas

## 📈 Monitoramento

### Logs do Sistema
```
📦 Cache HIT para chave: abc12345...
❌ Cache MISS para chave: def67890...
💾 Cache SET para chave: ghi11111...
⏰ Cache EXPIRADO para chave: jkl22222...
🧹 Cache FLUSHED - 3 entradas removidas
```

### Métricas Disponíveis
- **Total de entradas**: Número total de itens no cache
- **Entradas válidas**: Itens que não expiraram
- **Entradas expiradas**: Itens que expiraram mas ainda não foram removidos
- **Tamanho estimado**: Uso de memória em MB

## 🛠️ Comandos Úteis

### Verificar Status do Cache
```bash
curl -X GET "http://localhost:8000/metrics/cache/stats" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" | jq
```

### Limpar Cache Completo
```bash
curl -X POST "http://localhost:8000/metrics/cache/flush" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" | jq
```

### Limpar Apenas Expirados
```bash
curl -X POST "http://localhost:8000/metrics/cache/flush-expired" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" | jq
```

## ⚠️ Considerações Importantes

### 1. **Memória**
- Cache em memória (não persistente)
- Reinicia quando o servidor reinicia
- Monitorar uso de memória

### 2. **Consistência**
- Dados podem estar desatualizados (máximo 1 hora)
- Para dados críticos, usar flush do cache
- Considerar TTL menor para dados muito dinâmicos

### 3. **Escalabilidade**
- Cache local (não compartilhado entre instâncias)
- Para múltiplas instâncias, considerar Redis
- Monitorar crescimento do cache

## 🔄 Casos de Uso

### 1. **Desenvolvimento**
```bash
# Limpar cache para testar mudanças
curl -X POST "http://localhost:8000/metrics/cache/flush" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

### 2. **Produção**
```bash
# Verificar status do cache
curl -X GET "http://localhost:8000/metrics/cache/stats" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"

# Limpar entradas expiradas periodicamente
curl -X POST "http://localhost:8000/metrics/cache/flush-expired" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

### 3. **Manutenção**
```bash
# Limpar cache completo antes de atualizações
curl -X POST "http://localhost:8000/metrics/cache/flush" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
``` 