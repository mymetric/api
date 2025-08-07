# Atualização: Projeto bq-mktbr para Tabela Havaianas

## Resumo da Mudança

Implementei o suporte para a tabela `havaianas` usar o projeto BigQuery `bq-mktbr` em vez do projeto padrão `mymetric-hub-shopify`.

## Mudanças Implementadas

### 1. Função `get_project_name()` Atualizada

```python
def get_project_name(tablename: str) -> str:
    """Determina o nome do projeto baseado na tabela"""
    # Para tabelas específicas, usar projeto diferente
    if tablename in ['coffeemais', 'endogen']:
        project = 'mymetric-hub-shopify'
    elif tablename == 'havaianas':
        project = 'bq-mktbr'  # ✅ NOVO
    else:
        project = 'mymetric-hub-shopify'
    
    print(f"📊 Usando projeto: {project} para tabela: {tablename}")
    return project
```

### 2. Logs de Debug Adicionados

A função agora inclui logs para facilitar o debug:

```
📊 Usando projeto: bq-mktbr para tabela: havaianas
📊 Usando projeto: mymetric-hub-shopify para tabela: constance
```

## Mapeamento Atualizado

| Tabela | Projeto BigQuery | Dataset |
|--------|------------------|---------|
| `constance` | `mymetric-hub-shopify` | `dbt_join` |
| `coffeemais` | `mymetric-hub-shopify` | `dbt_join` |
| `endogen` | `mymetric-hub-shopify` | `dbt_join` |
| `havaianas` | `bq-mktbr` | `dbt_join` |
| `user_metrics` | `mymetric-hub-shopify` | `dbt_join` |
| Outras tabelas | `mymetric-hub-shopify` | `dbt_join` |

## Endpoints Afetados

Todos os endpoints que usam a função `get_project_name()` agora suportam a tabela `havaianas`:

1. **`/metrics/basic-data`**: Dados básicos do dashboard
2. **`/metrics/daily-metrics`**: Métricas diárias do funil
3. **`/metrics/orders`**: Orders detalhados
4. **`/metrics/traffic-categories`**: Categorias de tráfego

## Exemplo de Query para Havaianas

```sql
-- Para tabela 'havaianas'
SELECT *
FROM `bq-mktbr.dbt_join.havaianas_events_long`
WHERE event_date = '2024-01-15'

-- Para outras tabelas (exemplo: constance)
SELECT *
FROM `mymetric-hub-shopify.dbt_join.constance_events_long`
WHERE event_date = '2024-01-15'
```

## Estrutura Esperada no Projeto bq-mktbr

O projeto `bq-mktbr` deve conter as seguintes tabelas:

- `dbt_join.havaianas_events_long`
- `dbt_join.havaianas_orders_sessions`
- `dbt_aggregated.havaianas_daily_metrics`

## Teste da Implementação

Para testar se a mudança funcionou:

1. Fazer uma requisição para qualquer endpoint com `table_name: "havaianas"`
2. Verificar nos logs se aparece: `📊 Usando projeto: bq-mktbr para tabela: havaianas`
3. Verificar se a query é executada no projeto correto

## Exemplo de Requisição

```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-15",
  "table_name": "havaianas"
}
```

## Logs Esperados

```
🔓 Usuário com acesso total escolheu tabela: havaianas
📊 Usando projeto: bq-mktbr para tabela: havaianas
Executando query: SELECT ... FROM `bq-mktbr.dbt_join.havaianas_events_long` ...
```

## Status

✅ **Implementado**
- Suporte para tabela `havaianas` no projeto `bq-mktbr`
- Logs de debug para facilitar troubleshooting
- Documentação atualizada
- Todos os endpoints compatíveis

## Próximos Passos

1. Verificar se as tabelas existem no projeto `bq-mktbr`
2. Testar com dados reais da tabela `havaianas`
3. Monitorar logs para confirmar funcionamento 