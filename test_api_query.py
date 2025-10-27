from google.cloud import bigquery
from google.oauth2 import service_account
import os
from dotenv import load_dotenv

load_dotenv()

# Configurar credenciais
credentials = service_account.Credentials.from_service_account_file(
    'credentials/service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

client = bigquery.Client(credentials=credentials, project='mymetric-hub-shopify')

# Testar a query exata que o API deveria estar usando
project_name = 'mymetric-hub-shopify'
tablename = 'wtennis'
attribution_model = 'purchase'  # Convertido de 'Último Clique Não Direto'
date_condition = "event_date BETWEEN '2025-08-02' AND '2025-08-02'"

api_query = f"""
WITH session_data AS (
    SELECT
        event_date AS Data,
        extract(hour from created_at) as Hora,
        source as Origem,
        medium as `Midia`, 
        campaign as Campanha,
        page_location as `Pagina_de_Entrada`,
        content as `Conteudo`,
        coalesce(discount_code, 'Sem Cupom') as `Cupom`,
        traffic_category as `Cluster`,
        COUNT(*) as `Sessoes`,
        0 as `Adicoes_ao_Carrinho`,
        0 as `Pedidos`,
        0.0 as `Receita`,
        0 as `Pedidos_Pagos`,
        0.0 as `Receita_Paga`
    FROM `{project_name}.dbt_join.{tablename}_events_long`
    WHERE {date_condition} AND event_name = 'session'
    GROUP BY event_date, Hora, source, medium, campaign, page_location, content, discount_code, traffic_category
),
add_to_cart_data AS (
    SELECT
        event_date AS Data,
        extract(hour from created_at) as Hora,
        source as Origem,
        medium as `Midia`, 
        campaign as Campanha,
        page_location as `Pagina_de_Entrada`,
        content as `Conteudo`,
        coalesce(discount_code, 'Sem Cupom') as `Cupom`,
        traffic_category as `Cluster`,
        0 as `Sessoes`,
        COUNT(*) as `Adicoes_ao_Carrinho`,
        0 as `Pedidos`,
        0.0 as `Receita`,
        0 as `Pedidos_Pagos`,
        0.0 as `Receita_Paga`
    FROM `{project_name}.dbt_join.{tablename}_events_long`
    WHERE {date_condition} AND event_name = 'add_to_cart'
    GROUP BY event_date, Hora, source, medium, campaign, page_location, content, discount_code, traffic_category
),
purchase_data AS (
    SELECT
        event_date AS Data,
        extract(hour from created_at) as Hora,
        source as Origem,
        medium as `Midia`, 
        campaign as Campanha,
        page_location as `Pagina_de_Entrada`,
        content as `Conteudo`,
        coalesce(discount_code, 'Sem Cupom') as `Cupom`,
        traffic_category as `Cluster`,
        0 as `Sessoes`,
        0 as `Adicoes_ao_Carrinho`,
        COUNT(DISTINCT transaction_id) as `Pedidos`,
        SUM(value + shipping_value) as `Receita`,
        COUNT(DISTINCT CASE WHEN status in ('paid', 'authorized') THEN transaction_id END) as `Pedidos_Pagos`,
        SUM(CASE WHEN status in ('paid', 'authorized') THEN value + shipping_value ELSE 0 END) as `Receita_Paga`
    FROM `{project_name}.dbt_join.{tablename}_events_long`
    WHERE {date_condition} AND event_name = '{attribution_model}'
    GROUP BY event_date, Hora, source, medium, campaign, page_location, content, discount_code, traffic_category
)
SELECT * FROM (
    SELECT * FROM session_data
    UNION ALL
    SELECT * FROM add_to_cart_data
    UNION ALL
    SELECT * FROM purchase_data
)
ORDER BY Pedidos DESC
"""

print('Testando query exata do API...')
result = client.query(api_query)
rows = list(result.result())

print(f"Total de linhas retornadas: {len(rows)}")

# Contar linhas com receita > 0
revenue_rows = [row for row in rows if hasattr(row, 'Receita') and row.Receita and row.Receita > 0]
print(f"Linhas com receita > 0: {len(revenue_rows)}")

if revenue_rows:
    print("Primeiras 5 linhas com receita:")
    for i, row in enumerate(revenue_rows[:5]):
        print(f"  {i+1}. Receita={row.Receita}, Pedidos={row.Pedidos}, Origem={row.Origem}, Midia={row.Midia}")

# Calcular totais
total_revenue = sum(float(row.Receita) if row.Receita else 0.0 for row in rows)
total_orders = sum(int(row.Pedidos) if row.Pedidos else 0 for row in rows)
total_sessions = sum(int(row.Sessoes) if row.Sessoes else 0 for row in rows)
total_add_to_cart = sum(int(row.Adicoes_ao_Carrinho) if row.Adicoes_ao_Carrinho else 0 for row in rows)

print(f"\nTotais calculados:")
print(f"  Total Revenue: {total_revenue}")
print(f"  Total Orders: {total_orders}")
print(f"  Total Sessions: {total_sessions}")
print(f"  Total Add to Cart: {total_add_to_cart}") 