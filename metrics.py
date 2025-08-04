"""
Módulo de endpoints para métricas do dashboard
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from google.cloud import bigquery
from datetime import datetime, timedelta
import os

from utils import verify_token, TokenData, get_bigquery_client
from cache_manager import basic_data_cache

# Router para métricas
metrics_router = APIRouter(prefix="/metrics", tags=["metrics"])

# Modelos Pydantic para métricas
class MetricData(BaseModel):
    date: str
    value: float
    category: Optional[str] = None

class MetricResponse(BaseModel):
    metric_name: str
    data: List[MetricData]
    total: float
    average: float
    period: str

class DashboardMetrics(BaseModel):
    total_revenue: float
    total_orders: int
    average_order_value: float
    conversion_rate: float
    top_products: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]

# Novos modelos para dados básicos
class BasicDataRequest(BaseModel):
    start_date: str
    end_date: str
    attribution_model: Optional[str] = "Último Clique Não Direto"
    filters: Optional[Dict[str, Any]] = None
    table_name: Optional[str] = None  # Novo campo para permitir escolha da tabela

class BasicDataRow(BaseModel):
    Data: str
    Cluster: str
    Investimento: float
    Cliques: int
    Sessoes: int
    Adicoes_ao_Carrinho: int
    Pedidos: int
    Receita: float
    Pedidos_Pagos: int
    Receita_Paga: float
    Novos_Clientes: int
    Receita_Novos_Clientes: float

class BasicDataResponse(BaseModel):
    data: List[BasicDataRow]
    total_rows: int
    summary: Dict[str, Any]
    cache_info: Optional[Dict[str, Any]] = None

# Novos modelos para dados diários de métricas
class DailyMetricsRequest(BaseModel):
    start_date: str
    end_date: str
    table_name: Optional[str] = None

class DailyMetricsRow(BaseModel):
    Data: str
    Visualizacao_de_Item: int
    Adicionar_ao_Carrinho: int
    Iniciar_Checkout: int
    Adicionar_Informacao_de_Frete: int
    Adicionar_Informacao_de_Pagamento: int
    Pedido: int

class DailyMetricsResponse(BaseModel):
    data: List[DailyMetricsRow]
    total_rows: int
    summary: Dict[str, Any]
    cache_info: Optional[Dict[str, Any]] = None

def get_project_name(tablename: str) -> str:
    """Determina o nome do projeto baseado na tabela"""
    # Para tabelas específicas, usar projeto diferente
    if tablename in ['coffeemais', 'endogen']:
        return 'mymetric-hub-shopify'
    else:
        return 'mymetric-hub-shopify'

@metrics_router.post("/basic-data", response_model=BasicDataResponse)
async def get_basic_data(
    request: BasicDataRequest,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar dados básicos do dashboard com cache de 1 hora"""
    
    # Parâmetros para o cache
    cache_params = {
        'email': token.email,
        'start_date': request.start_date,
        'end_date': request.end_date,
        'attribution_model': request.attribution_model,
        'table_name': request.table_name
    }
    
    # Tentar buscar do cache primeiro
    cached_data = basic_data_cache.get(**cache_params)
    if cached_data:
        return BasicDataResponse(
            data=cached_data['data'],
            total_rows=cached_data['total_rows'],
            summary=cached_data['summary'],
            cache_info={
                'source': 'cache',
                'cached_at': cached_data.get('cached_at'),
                'ttl_hours': 1
            }
        )
    
    # Se não estiver no cache, buscar do BigQuery
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        # Buscar informações do usuário
        user_query = f"""
        SELECT tablename, access_control
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", token.email),
            ]
        )
        
        user_result = client.query(user_query, job_config=job_config)
        user_data = list(user_result.result())
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user_tablename = user_data[0].tablename
        access_control = user_data[0].access_control
        
        # Determinar qual tabela usar
        if user_tablename == 'all':
            # Usuário tem acesso a todas as tabelas
            if request.table_name:
                # Usuário escolheu uma tabela específica
                tablename = request.table_name
                print(f"🔓 Usuário com acesso total escolheu tabela: {tablename}")
            else:
                # Usar tabela padrão (constance)
                tablename = 'constance'
                print(f"🔓 Usuário com acesso total usando tabela padrão: {tablename}")
        else:
            # Usuário tem acesso limitado a uma tabela específica
            if request.table_name and request.table_name != user_tablename:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode acessar '{request.table_name}'"
                )
            tablename = user_tablename
            print(f"🔒 Usuário com acesso limitado usando tabela: {tablename}")

        # Processar modelo de atribuição
        attribution_model = request.attribution_model or 'Último Clique Não Direto'
        
        if attribution_model == 'Último Clique Não Direto':
            attribution_model = 'purchase'
        elif attribution_model == 'Primeiro Clique':
            attribution_model = 'fs_purchase'
        elif attribution_model == 'Assinaturas' and tablename == 'coffeemais':
            attribution_model = 'purchase_subscription'
        
        # Determinar projeto
        project_name = get_project_name(tablename)
        
        # Construir condição de data
        start_date = request.start_date
        end_date = request.end_date
        
        if start_date == end_date:
            date_condition = f"event_date = '{start_date}'"
        else:
            date_condition = f"event_date between '{start_date}' and '{end_date}'"
        
        # Construir query base
        if tablename == 'endogen':
            base_query = f"""
                SELECT
                    event_date AS Data,
                    traffic_category `Cluster`,
                    SUM(CASE WHEN event_name = 'paid_media' then value else 0 end) `Investimento`,
                    SUM(CASE WHEN event_name = 'paid_media' then clicks else 0 end) `Cliques`,
                    COUNTIF(event_name = 'session') `Sessoes`,
                    COUNTIF(event_name = 'add_to_cart') `Adicoes_ao_Carrinho`,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' then transaction_id end) `Pedidos`,
                    SUM(CASE WHEN event_name = '{attribution_model}' then value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) end) `Receita`,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') THEN transaction_id END) `Pedidos_Pagos`,
                    SUM(CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') THEN value ELSE 0 END) `Receita_Paga`,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') and transaction_no = 1 THEN transaction_id END) `Novos_Clientes`,
                    SUM(CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') and transaction_no = 1 THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) `Receita_Novos_Clientes`"""
        else:
            base_query = f"""
                SELECT
                    event_date AS Data,
                    traffic_category `Cluster`,
                    SUM(CASE WHEN event_name = 'paid_media' then value else 0 end) `Investimento`,
                    SUM(CASE WHEN event_name = 'paid_media' then clicks else 0 end) `Cliques`,
                    COUNTIF(event_name = 'session') `Sessoes`,
                    COUNTIF(event_name = 'add_to_cart') `Adicoes_ao_Carrinho`,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' then transaction_id end) `Pedidos`,
                    SUM(CASE WHEN event_name = '{attribution_model}' then value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) end) `Receita`,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') THEN transaction_id END) `Pedidos_Pagos`,
                    SUM(CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) `Receita_Paga`,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') and transaction_no = 1 THEN transaction_id END) `Novos_Clientes`,
                    SUM(CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') and transaction_no = 1 THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) `Receita_Novos_Clientes`"""

        # Query completa
        query = f"""
            {base_query}
            FROM `{project_name}.dbt_join.{tablename}_events_long`
            WHERE {date_condition}
            GROUP BY ALL
            ORDER BY Pedidos DESC
        """
        
        print(f"Executando query: {query}")
        
        # Executar query
        result = client.query(query)
        rows = list(result.result())
        
        # Converter para formato de resposta
        data = []
        total_investimento = 0
        total_receita = 0
        total_pedidos = 0
        
        for row in rows:
            data_row = BasicDataRow(
                Data=str(row.Data),
                Cluster=str(row.Cluster) if row.Cluster else "Sem Categoria",
                Investimento=float(row.Investimento or 0),
                Cliques=int(row.Cliques or 0),
                Sessoes=int(row.Sessoes or 0),
                Adicoes_ao_Carrinho=int(row.Adicoes_ao_Carrinho or 0),
                Pedidos=int(row.Pedidos or 0),
                Receita=float(row.Receita or 0),
                Pedidos_Pagos=int(row.Pedidos_Pagos or 0),
                Receita_Paga=float(row.Receita_Paga or 0),
                Novos_Clientes=int(row.Novos_Clientes or 0),
                Receita_Novos_Clientes=float(row.Receita_Novos_Clientes or 0)
            )
            data.append(data_row)
            
            # Calcular totais
            total_investimento += data_row.Investimento
            total_receita += data_row.Receita
            total_pedidos += data_row.Pedidos
        
        # Criar resumo
        summary = {
            "total_investimento": total_investimento,
            "total_receita": total_receita,
            "total_pedidos": total_pedidos,
            "roas": total_receita / total_investimento if total_investimento > 0 else 0,
            "ticket_medio": total_receita / total_pedidos if total_pedidos > 0 else 0,
            "periodo": f"{start_date} a {end_date}",
            "tablename": tablename,
            "user_access": "all" if user_tablename == 'all' else "limited",
            "attribution_model": request.attribution_model
        }
        
        # Preparar resposta
        response_data = {
            'data': [row.dict() for row in data],
            'total_rows': len(data),
            'summary': summary,
            'cached_at': datetime.now().isoformat()
        }
        
        # Armazenar no cache
        basic_data_cache.set(response_data, **cache_params)
        
        return BasicDataResponse(
            data=data,
            total_rows=len(data),
            summary=summary,
            cache_info={
                'source': 'database',
                'cached_at': response_data['cached_at'],
                'ttl_hours': 1
            }
        )
        
    except Exception as e:
        print(f"Erro ao buscar dados básicos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.post("/daily-metrics", response_model=DailyMetricsResponse)
async def get_daily_metrics(
    request: DailyMetricsRequest,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar dados diários de métricas do funil de conversão"""
    
    # Se não estiver no cache, buscar do BigQuery
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        # Buscar informações do usuário
        user_query = f"""
        SELECT tablename, access_control
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", token.email),
            ]
        )
        
        user_result = client.query(user_query, job_config=job_config)
        user_data = list(user_result.result())
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user_tablename = user_data[0].tablename
        access_control = user_data[0].access_control
        
        # Determinar qual tabela usar
        if user_tablename == 'all':
            # Usuário tem acesso a todas as tabelas
            if request.table_name:
                # Usuário escolheu uma tabela específica
                tablename = request.table_name
                print(f"🔓 Usuário com acesso total escolheu tabela: {tablename}")
            else:
                # Usar tabela padrão (constance)
                tablename = 'constance'
                print(f"🔓 Usuário com acesso total usando tabela padrão: {tablename}")
        else:
            # Usuário tem acesso limitado a uma tabela específica
            if request.table_name and request.table_name != user_tablename:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode acessar '{request.table_name}'"
                )
            tablename = user_tablename
            print(f"🔒 Usuário com acesso limitado usando tabela: {tablename}")

        # Determinar projeto
        project_name = get_project_name(tablename)
        
        # Construir condição de data
        start_date = request.start_date
        end_date = request.end_date
        
        if start_date == end_date:
            date_condition = f"event_date = '{start_date}'"
        else:
            date_condition = f"event_date between '{start_date}' and '{end_date}'"
        
        # Query para dados diários de métricas
        query = f"""
        SELECT 
            event_date `Data`,
            view_item `Visualizacao_de_Item`,
            add_to_cart `Adicionar_ao_Carrinho`,
            begin_checkout `Iniciar_Checkout`,
            add_shipping_info `Adicionar_Informacao_de_Frete`,
            add_payment_info `Adicionar_Informacao_de_Pagamento`,
            purchase `Pedido`
        FROM `{project_name}.dbt_aggregated.{tablename}_daily_metrics`
        WHERE {date_condition}
        ORDER BY event_date
        """
        
        print(f"Executando query daily-metrics: {query}")
        
        # Executar query
        result = client.query(query)
        rows = list(result.result())
        
        # Converter para formato de resposta
        data = []
        total_view_item = 0
        total_add_to_cart = 0
        total_begin_checkout = 0
        total_add_shipping_info = 0
        total_add_payment_info = 0
        total_purchase = 0
        
        for row in rows:
            data_row = DailyMetricsRow(
                Data=str(row.Data),
                Visualizacao_de_Item=int(row.Visualizacao_de_Item or 0),
                Adicionar_ao_Carrinho=int(row.Adicionar_ao_Carrinho or 0),
                Iniciar_Checkout=int(row.Iniciar_Checkout or 0),
                Adicionar_Informacao_de_Frete=int(row.Adicionar_Informacao_de_Frete or 0),
                Adicionar_Informacao_de_Pagamento=int(row.Adicionar_Informacao_de_Pagamento or 0),
                Pedido=int(row.Pedido or 0)
            )
            data.append(data_row)
            
            # Calcular totais
            total_view_item += data_row.Visualizacao_de_Item
            total_add_to_cart += data_row.Adicionar_ao_Carrinho
            total_begin_checkout += data_row.Iniciar_Checkout
            total_add_shipping_info += data_row.Adicionar_Informacao_de_Frete
            total_add_payment_info += data_row.Adicionar_Informacao_de_Pagamento
            total_purchase += data_row.Pedido
        
        # Calcular taxas de conversão
        conversion_rates = {}
        if total_view_item > 0:
            conversion_rates['view_to_cart'] = (total_add_to_cart / total_view_item) * 100
            conversion_rates['view_to_checkout'] = (total_begin_checkout / total_view_item) * 100
            conversion_rates['view_to_purchase'] = (total_purchase / total_view_item) * 100
        
        if total_add_to_cart > 0:
            conversion_rates['cart_to_checkout'] = (total_begin_checkout / total_add_to_cart) * 100
            conversion_rates['cart_to_purchase'] = (total_purchase / total_add_to_cart) * 100
        
        if total_begin_checkout > 0:
            conversion_rates['checkout_to_purchase'] = (total_purchase / total_begin_checkout) * 100
        
        # Criar resumo
        summary = {
            "total_view_item": total_view_item,
            "total_add_to_cart": total_add_to_cart,
            "total_begin_checkout": total_begin_checkout,
            "total_add_shipping_info": total_add_shipping_info,
            "total_add_payment_info": total_add_payment_info,
            "total_purchase": total_purchase,
            "conversion_rates": conversion_rates,
            "periodo": f"{start_date} a {end_date}",
            "tablename": tablename,
            "user_access": "all" if user_tablename == 'all' else "limited"
        }
        
        return DailyMetricsResponse(
            data=data,
            total_rows=len(data),
            summary=summary,
            cache_info={
                'source': 'database',
                'cached_at': datetime.now().isoformat(),
                'ttl_hours': 1
            }
        )
        
    except Exception as e:
        print(f"Erro ao buscar dados diários de métricas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(token: TokenData = Depends(verify_token)):
    """Endpoint para buscar métricas do dashboard principal"""
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        # Buscar informações do usuário para determinar tabela
        user_query = f"""
        SELECT tablename, access_control
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", token.email),
            ]
        )
        
        user_result = client.query(user_query, job_config=job_config)
        user_data = list(user_result.result())
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user_table = user_data[0].tablename
        access_control = user_data[0].access_control
        
        # Query para métricas do dashboard (exemplo genérico)
        # Você pode adaptar conforme sua estrutura de dados
        dashboard_query = f"""
        SELECT 
            COALESCE(SUM(revenue), 0) as total_revenue,
            COALESCE(COUNT(DISTINCT order_id), 0) as total_orders,
            COALESCE(AVG(revenue), 0) as avg_order_value,
            COALESCE(COUNT(DISTINCT customer_id) * 100.0 / NULLIF(COUNT(DISTINCT session_id), 0), 0) as conversion_rate
        FROM `{user_table}`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        """
        
        dashboard_result = client.query(dashboard_query)
        dashboard_data = list(dashboard_result.result())
        
        if not dashboard_data:
            # Dados de exemplo se não houver dados reais
            dashboard_metrics = {
                "total_revenue": 0.0,
                "total_orders": 0,
                "average_order_value": 0.0,
                "conversion_rate": 0.0
            }
        else:
            row = dashboard_data[0]
            dashboard_metrics = {
                "total_revenue": float(row.total_revenue or 0),
                "total_orders": int(row.total_orders or 0),
                "average_order_value": float(row.avg_order_value or 0),
                "conversion_rate": float(row.conversion_rate or 0)
            }
        
        # Buscar produtos mais vendidos
        top_products_query = f"""
        SELECT 
            product_name,
            SUM(quantity) as total_quantity,
            SUM(revenue) as total_revenue
        FROM `{user_table}`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        GROUP BY product_name
        ORDER BY total_revenue DESC
        LIMIT 5
        """
        
        try:
            top_products_result = client.query(top_products_query)
            top_products_data = list(top_products_result.result())
            
            top_products = []
            for row in top_products_data:
                top_products.append({
                    "name": row.product_name,
                    "quantity": int(row.total_quantity or 0),
                    "revenue": float(row.total_revenue or 0)
                })
        except:
            # Dados de exemplo se a query falhar
            top_products = [
                {"name": "Produto A", "quantity": 100, "revenue": 5000.0},
                {"name": "Produto B", "quantity": 80, "revenue": 4000.0},
                {"name": "Produto C", "quantity": 60, "revenue": 3000.0}
            ]
        
        # Buscar atividade recente
        recent_activity_query = f"""
        SELECT 
            order_id,
            customer_name,
            revenue,
            date
        FROM `{user_table}`
        ORDER BY date DESC
        LIMIT 10
        """
        
        try:
            recent_activity_result = client.query(recent_activity_query)
            recent_activity_data = list(recent_activity_result.result())
            
            recent_activity = []
            for row in recent_activity_data:
                recent_activity.append({
                    "order_id": row.order_id,
                    "customer": row.customer_name,
                    "amount": float(row.revenue or 0),
                    "date": str(row.date)
                })
        except:
            # Dados de exemplo se a query falhar
            recent_activity = [
                {"order_id": "ORD001", "customer": "João Silva", "amount": 150.0, "date": "2024-01-15"},
                {"order_id": "ORD002", "customer": "Maria Santos", "amount": 200.0, "date": "2024-01-14"},
                {"order_id": "ORD003", "customer": "Pedro Costa", "amount": 75.0, "date": "2024-01-13"}
            ]
        
        return DashboardMetrics(
            total_revenue=dashboard_metrics["total_revenue"],
            total_orders=dashboard_metrics["total_orders"],
            average_order_value=dashboard_metrics["average_order_value"],
            conversion_rate=dashboard_metrics["conversion_rate"],
            top_products=top_products,
            recent_activity=recent_activity
        )
        
    except Exception as e:
        print(f"Erro ao buscar métricas do dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@metrics_router.get("/revenue", response_model=MetricResponse)
async def get_revenue_metrics(
    period: str = "30d",
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar métricas de receita"""
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        # Buscar tabela do usuário
        user_query = f"""
        SELECT tablename
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", token.email),
            ]
        )
        
        user_result = client.query(user_query, job_config=job_config)
        user_data = list(user_result.result())
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user_table = user_data[0].tablename
        
        # Definir período baseado no parâmetro
        if period == "7d":
            interval = "INTERVAL 7 DAY"
        elif period == "30d":
            interval = "INTERVAL 30 DAY"
        elif period == "90d":
            interval = "INTERVAL 90 DAY"
        else:
            interval = "INTERVAL 30 DAY"
        
        # Query para receita
        revenue_query = f"""
        SELECT 
            DATE(date) as date,
            SUM(revenue) as daily_revenue
        FROM `{user_table}`
        WHERE date >= DATE_SUB(CURRENT_DATE(), {interval})
        GROUP BY DATE(date)
        ORDER BY date
        """
        
        revenue_result = client.query(revenue_query)
        revenue_data = list(revenue_result.result())
        
        metric_data = []
        total_revenue = 0.0
        
        for row in revenue_data:
            daily_revenue = float(row.daily_revenue or 0)
            total_revenue += daily_revenue
            metric_data.append(MetricData(
                date=str(row.date),
                value=daily_revenue
            ))
        
        average_revenue = total_revenue / len(metric_data) if metric_data else 0.0
        
        return MetricResponse(
            metric_name="Receita Diária",
            data=metric_data,
            total=total_revenue,
            average=average_revenue,
            period=period
        )
        
    except Exception as e:
        print(f"Erro ao buscar métricas de receita: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@metrics_router.get("/orders", response_model=MetricResponse)
async def get_orders_metrics(
    period: str = "30d",
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar métricas de pedidos"""
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        # Buscar tabela do usuário
        user_query = f"""
        SELECT tablename
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", token.email),
            ]
        )
        
        user_result = client.query(user_query, job_config=job_config)
        user_data = list(user_result.result())
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user_table = user_data[0].tablename
        
        # Definir período
        if period == "7d":
            interval = "INTERVAL 7 DAY"
        elif period == "30d":
            interval = "INTERVAL 30 DAY"
        elif period == "90d":
            interval = "INTERVAL 90 DAY"
        else:
            interval = "INTERVAL 30 DAY"
        
        # Query para pedidos
        orders_query = f"""
        SELECT 
            DATE(date) as date,
            COUNT(DISTINCT order_id) as daily_orders
        FROM `{user_table}`
        WHERE date >= DATE_SUB(CURRENT_DATE(), {interval})
        GROUP BY DATE(date)
        ORDER BY date
        """
        
        orders_result = client.query(orders_query)
        orders_data = list(orders_result.result())
        
        metric_data = []
        total_orders = 0
        
        for row in orders_data:
            daily_orders = int(row.daily_orders or 0)
            total_orders += daily_orders
            metric_data.append(MetricData(
                date=str(row.date),
                value=float(daily_orders)
            ))
        
        average_orders = total_orders / len(metric_data) if metric_data else 0.0
        
        return MetricResponse(
            metric_name="Pedidos Diários",
            data=metric_data,
            total=float(total_orders),
            average=average_orders,
            period=period
        )
        
    except Exception as e:
        print(f"Erro ao buscar métricas de pedidos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@metrics_router.get("/customers")
async def get_customer_metrics(token: TokenData = Depends(verify_token)):
    """Endpoint para buscar métricas de clientes"""
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        # Buscar tabela do usuário
        user_query = f"""
        SELECT tablename
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", token.email),
            ]
        )
        
        user_result = client.query(user_query, job_config=job_config)
        user_data = list(user_result.result())
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user_table = user_data[0].tablename
        
        # Query para métricas de clientes
        customers_query = f"""
        SELECT 
            COUNT(DISTINCT customer_id) as total_customers,
            COUNT(DISTINCT CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN customer_id END) as new_customers_30d,
            COUNT(DISTINCT CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) THEN customer_id END) as new_customers_7d,
            AVG(revenue) as avg_customer_value
        FROM `{user_table}`
        """
        
        customers_result = client.query(customers_query)
        customers_data = list(customers_result.result())
        
        if customers_data:
            row = customers_data[0]
            return {
                "total_customers": int(row.total_customers or 0),
                "new_customers_30d": int(row.new_customers_30d or 0),
                "new_customers_7d": int(row.new_customers_7d or 0),
                "avg_customer_value": float(row.avg_customer_value or 0)
            }
        else:
            return {
                "total_customers": 0,
                "new_customers_30d": 0,
                "new_customers_7d": 0,
                "avg_customer_value": 0.0
            }
        
    except Exception as e:
        print(f"Erro ao buscar métricas de clientes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        ) 

@metrics_router.get("/available-tables")
async def get_available_tables(token: TokenData = Depends(verify_token)):
    """Endpoint para listar tabelas disponíveis para o usuário"""
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        # Buscar informações do usuário
        user_query = f"""
        SELECT tablename, access_control
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", token.email),
            ]
        )
        
        user_result = client.query(user_query, job_config=job_config)
        user_data = list(user_result.result())
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user_tablename = user_data[0].tablename
        
        if user_tablename == 'all':
            # Usuário tem acesso a todas as tabelas - listar todas disponíveis
            try:
                # Listar tabelas no dataset dbt_join que terminam com _events_long
                tables_query = """
                SELECT table_id
                FROM `mymetric-hub-shopify.dbt_join.__TABLES__`
                WHERE table_id LIKE '%_events_long'
                ORDER BY table_id
                """
                
                tables_result = client.query(tables_query)
                tables_data = list(tables_result.result())
                
                available_tables = []
                for row in tables_data:
                    # Remover o sufixo _events_long para mostrar nome limpo
                    table_name = row.table_id.replace('_events_long', '')
                    available_tables.append({
                        "table_id": row.table_id,
                        "table_name": table_name,
                        "display_name": table_name.title()
                    })
                
                return {
                    "user_access": "all",
                    "available_tables": available_tables,
                    "message": "Usuário tem acesso a todas as tabelas"
                }
                
            except Exception as e:
                # Se não conseguir listar, retornar tabelas conhecidas
                known_tables = [
                    {"table_id": "constance_events_long", "table_name": "constance", "display_name": "Constance"},
                    {"table_id": "coffeemais_events_long", "table_name": "coffeemais", "display_name": "Coffee Mais"},
                    {"table_id": "endogen_events_long", "table_name": "endogen", "display_name": "Endogen"},
                    {"table_id": "user_metrics_events_long", "table_name": "user_metrics", "display_name": "User Metrics"}
                ]
                
                return {
                    "user_access": "all",
                    "available_tables": known_tables,
                    "message": "Lista de tabelas conhecidas (não foi possível verificar no BigQuery)"
                }
        else:
            # Usuário tem acesso limitado - retornar apenas sua tabela
            return {
                "user_access": "limited",
                "available_tables": [
                    {
                        "table_id": f"{user_tablename}_events_long",
                        "table_name": user_tablename,
                        "display_name": user_tablename.title()
                    }
                ],
                "message": f"Usuário tem acesso limitado à tabela {user_tablename}"
            }
        
    except Exception as e:
        print(f"Erro ao listar tabelas disponíveis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )   

@metrics_router.post("/cache/flush")
async def flush_cache(token: TokenData = Depends(verify_token)):
    """Endpoint para fazer flush completo do cache"""
    try:
        # Verificar se o usuário é admin
        user_query = f"""
        SELECT admin
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", token.email),
            ]
        )
        
        client = get_bigquery_client()
        user_result = client.query(user_query, job_config=job_config)
        user_data = list(user_result.result())
        
        if not user_data or not user_data[0].admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas administradores podem fazer flush do cache"
            )
        
        # Fazer flush do cache
        stats = basic_data_cache.flush()
        
        return {
            "message": "Cache limpo com sucesso",
            "stats": stats
        }
        
    except Exception as e:
        print(f"Erro ao fazer flush do cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.post("/cache/flush-expired")
async def flush_expired_cache(token: TokenData = Depends(verify_token)):
    """Endpoint para remover apenas entradas expiradas do cache"""
    try:
        # Verificar se o usuário é admin
        user_query = f"""
        SELECT admin
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", token.email),
            ]
        )
        
        client = get_bigquery_client()
        user_result = client.query(user_query, job_config=job_config)
        user_data = list(user_result.result())
        
        if not user_data or not user_data[0].admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas administradores podem gerenciar o cache"
            )
        
        # Fazer flush apenas das entradas expiradas
        stats = basic_data_cache.flush_expired()
        
        return {
            "message": "Entradas expiradas removidas com sucesso",
            "stats": stats
        }
        
    except Exception as e:
        print(f"Erro ao fazer flush de entradas expiradas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.get("/cache/stats")
async def get_cache_stats(token: TokenData = Depends(verify_token)):
    """Endpoint para obter estatísticas do cache"""
    try:
        # Verificar se o usuário é admin
        user_query = f"""
        SELECT admin
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", token.email),
            ]
        )
        
        client = get_bigquery_client()
        user_result = client.query(user_query, job_config=job_config)
        user_data = list(user_result.result())
        
        if not user_data or not user_data[0].admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas administradores podem ver estatísticas do cache"
            )
        
        # Obter estatísticas do cache
        stats = basic_data_cache.get_stats()
        
        return {
            "message": "Estatísticas do cache",
            "stats": stats
        }
        
    except Exception as e:
        print(f"Erro ao obter estatísticas do cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        ) 