# Mapeamento de Projetos BigQuery por Tabela

## Função `get_project_name()`

A função `get_project_name(tablename: str)` determina qual projeto do BigQuery deve ser usado baseado no nome da tabela.

## Mapeamento Atual

| Tabela | Projeto BigQuery | Dataset |
|--------|------------------|---------|
| `constance` | `mymetric-hub-shopify` | `dbt_join` |
| `coffeemais` | `mymetric-hub-shopify` | `dbt_join` |
| `endogen` | `mymetric-hub-shopify` | `dbt_join` |
| `havaianas` | `bq-mktbr` | `dbt_join` |
| `user_metrics` | `mymetric-hub-shopify` | `dbt_join` |
| Outras tabelas | `mymetric-hub-shopify` | `dbt_join` |

## Implementação

```python
def get_project_name(tablename: str) -> str:
    """Determina o nome do projeto baseado na tabela"""
    # Para tabelas específicas, usar projeto diferente
    if tablename in ['coffeemais', 'endogen']:
        project = 'mymetric-hub-shopify'
    elif tablename == 'havaianas':
        project = 'bq-mktbr'
    else:
        project = 'mymetric-hub-shopify'
    
    print(f"📊 Usando projeto: {project} para tabela: {tablename}")
    return project
```

## Uso nos Endpoints

A função é usada em todos os endpoints que fazem consultas ao BigQuery:

1. **`/basic-data`**: Para dados básicos do dashboard
2. **`/daily-metrics`**: Para métricas diárias do funil
3. **`/orders`**: Para orders detalhados
4. **`/traffic-categories`**: Para categorias de tráfego

## Exemplo de Query

```sql
-- Para tabela 'havaianas'
SELECT *
FROM `bq-mktbr.dbt_join.havaianas_events_long`
WHERE event_date = '2024-01-15'

-- Para outras tabelas
SELECT *
FROM `mymetric-hub-shopify.dbt_join.constance_events_long`
WHERE event_date = '2024-01-15'
```

## Estrutura das Tabelas

Todas as tabelas seguem o padrão:
- **Tabela de eventos**: `{tablename}_events_long`
- **Tabela de orders**: `{tablename}_orders_sessions`
- **Tabela de métricas diárias**: `{tablename}_daily_metrics`

## Configuração de Usuários

A tabela de configuração de usuários está sempre no projeto `mymetric-hub-shopify`:

```sql
SELECT tablename, access_control
FROM `mymetric-hub-shopify.dbt_config.users`
WHERE email = @email
```

## Adicionando Novas Tabelas

Para adicionar uma nova tabela com projeto diferente:

1. Adicionar a condição na função `get_project_name()`
2. Atualizar esta documentação
3. Verificar se as tabelas existem no projeto correto

## Logs de Debug

Os logs mostram qual projeto está sendo usado:

```
🔓 Usuário com acesso total escolheu tabela: havaianas
📊 Usando projeto: bq-mktbr
```

## Status

✅ **Implementado**
- Mapeamento para tabela `havaianas` → projeto `bq-mktbr`
- Mapeamento para outras tabelas → projeto `mymetric-hub-shopify`
- Função centralizada para determinar projeto 