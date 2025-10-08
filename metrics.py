"""
Módulo de endpoints para métricas do dashboard
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from google.cloud import bigquery
from datetime import datetime, timedelta
import os
import math

from utils import verify_token, TokenData, get_bigquery_client
from cache_manager import basic_data_cache, daily_metrics_cache, orders_cache, detailed_data_cache, product_trend_cache, ads_campaigns_results_cache, realtime_cache, last_request_manager

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
    Plataforma: str
    city: str = ""
    region: str = ""
    country: str = ""
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
    # Novos campos para métricas de assinatura
    Pedidos_Assinatura_Anual_Inicial: int = 0
    Receita_Assinatura_Anual_Inicial: float = 0.0
    Pedidos_Assinatura_Mensal_Inicial: int = 0
    Receita_Assinatura_Mensal_Inicial: float = 0.0
    Pedidos_Assinatura_Anual_Recorrente: int = 0
    Receita_Assinatura_Anual_Recorrente: float = 0.0
    Pedidos_Assinatura_Mensal_Recorrente: int = 0
    Receita_Assinatura_Mensal_Recorrente: float = 0.0

class BasicDataResponse(BaseModel):
    total_rows: int
    summary: Dict[str, Any]
    data: List[BasicDataRow]
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

# Novos modelos para orders
class OrdersRequest(BaseModel):
    start_date: str
    end_date: str
    table_name: Optional[str] = None
    limit: Optional[int] = 1000
    offset: Optional[int] = 0
    traffic_category: Optional[str] = None
    fs_traffic_category: Optional[str] = None
    fsm_traffic_category: Optional[str] = None

class OrderRow(BaseModel):
    Horario: str
    ID_da_Transacao: str
    Primeiro_Nome: str
    Status: str
    Receita: float
    Canal: str
    
    # Campos do último clique
    Categoria_de_Trafico: str
    Origem: str
    Midia: str
    Campanha: str
    Conteudo: str
    Pagina_de_Entrada: str
    Parametros_de_URL: str
    
    # Campos do primeiro clique
    Categoria_de_Trafico_Primeiro_Clique: str
    Origem_Primeiro_Clique: str
    Midia_Primeiro_Clique: str
    Campanha_Primeiro_Clique: str
    Conteudo_Primeiro_Clique: str
    Pagina_de_Entrada_Primeiro_Clique: str
    Parametros_de_URL_Primeiro_Clique: str
    
    # Campos do primeiro lead
    Categoria_de_Trafico_Primeiro_Lead: str
    Origem_Primeiro_Lead: str
    Midia_Primeiro_Lead: str
    Campanha_Primeiro_Lead: str
    Conteudo_Primeiro_Lead: str
    Pagina_de_Entrada_Primeiro_Lead: str
    Parametros_de_URL_Primeiro_Lead: str

class OrdersResponse(BaseModel):
    data: List[OrderRow]
    total_rows: int
    summary: Dict[str, Any]

# Modelos para metas do usuário
class UserGoalsRequest(BaseModel):
    table_name: str

class UserGoalsResponse(BaseModel):
    username: str
    goals: Dict[str, Any]
    message: str

class UpdateUserGoalsRequest(BaseModel):
    username: str
    goals: Dict[str, Any]


# Novos modelos para dados detalhados
class DetailedDataRequest(BaseModel):
    start_date: str
    end_date: str
    attribution_model: Optional[str] = "purchase"
    table_name: Optional[str] = None
    limit: Optional[int] = 10000  # Limitar resultados
    offset: Optional[int] = 0    # Paginação
    order_by: Optional[str] = "Pedidos"  # Campo para ordenação

class DetailedDataRow(BaseModel):
    Data: str
    Hora: int
    Origem: str
    Midia: str
    Campanha: str
    Pagina_de_Entrada: str
    Conteudo: str
    Cupom: str
    Cluster: str
    Sessoes: int
    Adicoes_ao_Carrinho: int
    Pedidos: int
    Receita: float
    Pedidos_Pagos: int
    Receita_Paga: float

class DetailedDataResponse(BaseModel):
    summary: Dict[str, Any]
    total_rows: int
    data: List[DetailedDataRow]
    cache_info: Optional[Dict[str, Any]] = None
    pagination: Optional[Dict[str, Any]] = None

# Modelos para product trend
class ProductTrendRequest(BaseModel):
    table_name: str
    limit: Optional[int] = 100
    offset: Optional[int] = 0
    order_by: Optional[str] = "purchases_week_4"

class ProductTrendRow(BaseModel):
    item_id: str
    item_name: str
    purchases_week_1: int
    purchases_week_2: int
    purchases_week_3: int
    purchases_week_4: int
    percent_change_w1_w2: float
    percent_change_w2_w3: float
    percent_change_w3_w4: float
    trend_status: str
    trend_consistency: str
    # Campos de benchmark
    benchmark_week_1: Optional[float] = Field(default=None, json_schema_extra={"example": None})
    benchmark_week_2: Optional[float] = Field(default=None, json_schema_extra={"example": None})
    benchmark_week_3: Optional[float] = Field(default=None, json_schema_extra={"example": None})
    benchmark_week_4: Optional[float] = Field(default=None, json_schema_extra={"example": None})
    # Campos de clicks
    clicks_week_1: Optional[int] = Field(default=None, json_schema_extra={"example": None})
    clicks_week_2: Optional[int] = Field(default=None, json_schema_extra={"example": None})
    clicks_week_3: Optional[int] = Field(default=None, json_schema_extra={"example": None})
    clicks_week_4: Optional[int] = Field(default=None, json_schema_extra={"example": None})
    # Campos específicos para Havaianas
    size_score_week_1: Optional[float] = None
    size_score_week_2: Optional[float] = None
    size_score_week_3: Optional[float] = None
    size_score_week_4: Optional[float] = None
    size_score_trend_status: Optional[str] = None

class ProductTrendResponse(BaseModel):
    data: List[ProductTrendRow]
    total_rows: int
    summary: Dict[str, Any]
    pagination: Optional[Dict[str, Any]] = None
    cache_info: Optional[Dict[str, Any]] = None

# Novos modelos para ads campaigns results
class AdsCampaignsResultsRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    table_name: Optional[str] = None
    last_cache: Optional[bool] = False
    force_refresh: Optional[bool] = False

class AdsCampaignsResultsRow(BaseModel):
    platform: str
    campaign_name: str
    date: str
    cost: float
    impressions: int
    clicks: int
    leads: int
    transactions: int
    revenue: float
    transactions_first: int
    revenue_first: float
    transactions_origin_stack: int
    revenue_origin_stack: float
    transactions_first_origin_stack: int
    revenue_first_origin_stack: float
    # Novos campos para métricas de assinatura
    first_montly_subscriptions: int = 0
    first_annual_subscriptions: int = 0
    recurring_montly_subscriptions: int = 0
    recurring_annual_subscriptions: int = 0
    first_montly_revenue: float = 0.0
    first_annual_revenue: float = 0.0
    recurring_montly_revenue: float = 0.0
    recurring_annual_revenue: float = 0.0
    fsm_first_montly_subscriptions: int = 0
    fsm_first_annual_subscriptions: int = 0
    fsm_recurring_montly_subscriptions: int = 0
    fsm_recurring_annual_subscriptions: int = 0
    fsm_first_montly_revenue: float = 0.0
    fsm_first_annual_revenue: float = 0.0
    fsm_recurring_montly_revenue: float = 0.0
    fsm_recurring_annual_revenue: float = 0.0

class AdsCampaignsResultsResponse(BaseModel):
    total_rows: int
    summary: Dict[str, Any]
    data: List[AdsCampaignsResultsRow]
    cache_info: Optional[Dict[str, Any]] = None

# Novos modelos para ads creatives results
class AdsCreativesResultsRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    table_name: Optional[str] = None
    last_cache: Optional[bool] = False
    force_refresh: Optional[bool] = False

class AdsCreativesResultsRow(BaseModel):
    platform: str
    campaign_name: str
    adset_id: int
    adset_name: str
    ad_id: int
    ad_name: str
    date: str
    cost: float
    impressions: int
    clicks: int
    leads: int
    transactions: int
    revenue: float
    transactions_first: int
    revenue_first: float
    transactions_origin_stack: int
    revenue_origin_stack: float
    transactions_first_origin_stack: int
    revenue_first_origin_stack: float

class AdsCreativesResultsResponse(BaseModel):
    data: List[AdsCreativesResultsRow]
    total_rows: int
    summary: Dict[str, Any]
    cache_info: Optional[Dict[str, Any]] = None

# Novos modelos para realtime purchases items
class RealtimeRequest(BaseModel):
    table_name: Optional[str] = None
    limit: Optional[int] = None

class RealtimeRow(BaseModel):
    event_timestamp: str
    session_id: str
    transaction_id: str
    item_category: str
    item_name: str
    quantity: int
    item_revenue: float
    source: str
    medium: str
    campaign: str
    content: str
    term: str
    page_location: str
    traffic_category: str

class RealtimeResponse(BaseModel):
    data: List[RealtimeRow]
    total_rows: int
    summary: Dict[str, Any]
    cache_info: Optional[Dict[str, Any]] = None



# -------------------------------
# Shipping Calc Analytics (geral)
# -------------------------------
class ShippingCalcAnalyticsRow(BaseModel):
    event_date: Optional[str] = None
    zipcode: Optional[str] = None
    zipcode_region: Optional[str] = None
    calculations: Optional[int] = None
    calculations_freight_unavailable: Optional[int] = None
    transactions: Optional[int] = None
    revenue: Optional[float] = None

class ShippingCalcAnalyticsSummary(BaseModel):
    total_calculations: int = 0
    total_calculations_freight_unavailable: int = 0
    total_transactions: int = 0
    total_revenue: float = 0.0

class ShippingCalcAnalyticsResponse(BaseModel):
    summary: ShippingCalcAnalyticsSummary
    data: List[ShippingCalcAnalyticsRow]
    total_rows: int

class ShippingCalcAnalyticsRequest(BaseModel):
    table_name: Optional[str] = None
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD

# Modelos para leads_orders
class LeadsOrdersRequest(BaseModel):
    start_date: str
    end_date: str
    table_name: str

class LeadsOrdersRow(BaseModel):
    subscribe_timestamp: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    fsm_source: Optional[str] = None
    fsm_medium: Optional[str] = None
    fsm_campaign: Optional[str] = None
    transaction_id: Optional[str] = None
    purchase_timestamp: Optional[str] = None
    value: Optional[float] = None
    source: Optional[str] = None
    medium: Optional[str] = None
    campaign: Optional[str] = None
    days_between_subscribe_and_purchase: Optional[int] = None
    minutes_between_subscribe_and_purchase: Optional[int] = None

class LeadsOrdersResponse(BaseModel):
    data: List[LeadsOrdersRow]
    total_rows: int
    summary: Dict[str, Any]
    cache_info: Optional[Dict[str, Any]] = None

def _run_shipping_calc_query(client, project_name: str, tablename: str, start_date: Optional[str], end_date: Optional[str]) -> List[ShippingCalcAnalyticsRow]:
    where_clause = ""
    if start_date and end_date:
        if start_date == end_date:
            where_clause = f"\nWHERE event_date = '{start_date}'"
        else:
            where_clause = f"\nWHERE event_date BETWEEN '{start_date}' AND '{end_date}'"

    query = (
        "SELECT\n"
        "  event_date,\n"
        "  zipcode,\n"
        "  zipcode_region,\n"
        "  calculations,\n"
        "  calculations_freight_unavailable,\n"
        "  transactions,\n"
        "  revenue\n"
        f"FROM `{project_name}.dbt_aggregated.{tablename}_shipping_calc_analytics`" +
        where_clause +
        "\nORDER BY event_date DESC, zipcode"
    )

    query_job = client.query(query)
    results = list(query_job.result())

    data: List[ShippingCalcAnalyticsRow] = []
    for row in results:
        data.append(ShippingCalcAnalyticsRow(
            event_date=str(row.event_date) if getattr(row, "event_date", None) is not None else None,
            zipcode=str(row.zipcode) if getattr(row, "zipcode", None) is not None else None,
            zipcode_region=str(row.zipcode_region) if getattr(row, "zipcode_region", None) is not None else None,
            calculations=int(row.calculations) if getattr(row, "calculations", None) is not None else None,
            calculations_freight_unavailable=int(row.calculations_freight_unavailable) if getattr(row, "calculations_freight_unavailable", None) is not None else None,
            transactions=int(row.transactions) if getattr(row, "transactions", None) is not None else None,
            revenue=float(row.revenue) if getattr(row, "revenue", None) is not None else None,
        ))
    return data

def _calculate_shipping_calc_summary(data: List[ShippingCalcAnalyticsRow]) -> ShippingCalcAnalyticsSummary:
    """Calcula o sumário de totais dos dados de shipping calc analytics"""
    total_calculations = 0
    total_calculations_freight_unavailable = 0
    total_transactions = 0
    total_revenue = 0.0
    
    for row in data:
        if row.calculations is not None:
            total_calculations += row.calculations
        if row.calculations_freight_unavailable is not None:
            total_calculations_freight_unavailable += row.calculations_freight_unavailable
        if row.transactions is not None:
            total_transactions += row.transactions
        if row.revenue is not None:
            total_revenue += row.revenue
    
    return ShippingCalcAnalyticsSummary(
        total_calculations=total_calculations,
        total_calculations_freight_unavailable=total_calculations_freight_unavailable,
        total_transactions=total_transactions,
        total_revenue=total_revenue
    )

@metrics_router.get("/shipping-calc-analytics", response_model=ShippingCalcAnalyticsResponse)
async def shipping_calc_analytics(
    token: TokenData = Depends(verify_token),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    table_name: Optional[str] = None
):
    """
    Retorna métricas de cálculo de frete a partir da tabela
    `bq-mktbr.dbt_aggregated.havaianas_shipping_calc_analytics`.
    """
    try:
        client = get_bigquery_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro de conexão com o banco de dados"
            )

        # Buscar informações do usuário para determinar tablename permitido
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

        user_tablename = user_data[0].tablename

        if user_tablename == 'all':
            effective_tablename = table_name or 'constance'
        else:
            if table_name and table_name != user_tablename:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode acessar '{table_name}'"
                )
            effective_tablename = user_tablename

        project_name = get_project_name(effective_tablename)

        data = _run_shipping_calc_query(client, project_name, effective_tablename, start_date, end_date)
        summary = _calculate_shipping_calc_summary(data)

        return ShippingCalcAnalyticsResponse(
            summary=summary,
            data=data,
            total_rows=len(data)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro no método shipping_calc_analytics: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.post("/shipping-calc-analytics", response_model=ShippingCalcAnalyticsResponse)
async def shipping_calc_analytics_post(
    request: ShippingCalcAnalyticsRequest,
    token: TokenData = Depends(verify_token)
):
    """
    Versão POST do endpoint para compatibilidade de chamadas via POST.
    """
    try:
        client = get_bigquery_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro de conexão com o banco de dados"
            )

        # Buscar informações do usuário para determinar tablename permitido
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

        user_tablename = user_data[0].tablename
        if user_tablename == 'all':
            effective_tablename = request.table_name or 'constance'
        else:
            if request.table_name and request.table_name != user_tablename:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode acessar '{request.table_name}'"
                )
            effective_tablename = user_tablename

        project_name = get_project_name(effective_tablename)

        data = _run_shipping_calc_query(client, project_name, effective_tablename, request.start_date, request.end_date)
        summary = _calculate_shipping_calc_summary(data)
        return ShippingCalcAnalyticsResponse(
            summary=summary,
            data=data,
            total_rows=len(data)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro no método shipping_calc_analytics_post: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

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
                    traffic_category AS Cluster,
                    platform AS Plataforma,
                    city,
                    region,
                    country,
                    SUM(CASE WHEN event_name = 'paid_media' then value else 0 end) AS Investimento,
                    SUM(CASE WHEN event_name = 'paid_media' then clicks else 0 end) AS Cliques,
                    COUNTIF(event_name = 'session') AS Sessoes,
                    COUNTIF(event_name = 'add_to_cart') AS Adicoes_ao_Carrinho,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' then transaction_id end) AS Pedidos,
                    SUM(CASE WHEN event_name = '{attribution_model}' then value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) end) AS Receita,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') THEN transaction_id END) AS Pedidos_Pagos,
                    SUM(CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') THEN value ELSE 0 END) AS Receita_Paga,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') and transaction_no = 1 THEN transaction_id END) AS Novos_Clientes,
                    SUM(CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') and transaction_no = 1 THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Novos_Clientes,
                    -- Métricas de assinatura
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and order_type = 'first annual subscription' THEN transaction_id END) AS Pedidos_Assinatura_Anual_Inicial,
                    SUM(CASE WHEN event_name = '{attribution_model}' and order_type = 'first annual subscription' THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Assinatura_Anual_Inicial,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and order_type = 'first montly subscription' THEN transaction_id END) AS Pedidos_Assinatura_Mensal_Inicial,
                    SUM(CASE WHEN event_name = '{attribution_model}' and order_type = 'first montly subscription' THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Assinatura_Mensal_Inicial,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and order_type = 'recurring annual subscription' THEN transaction_id END) AS Pedidos_Assinatura_Anual_Recorrente,
                    SUM(CASE WHEN event_name = '{attribution_model}' and order_type = 'recurring annual subscription' THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Assinatura_Anual_Recorrente,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and order_type = 'recurring montly subscription' THEN transaction_id END) AS Pedidos_Assinatura_Mensal_Recorrente,
                    SUM(CASE WHEN event_name = '{attribution_model}' and order_type = 'recurring montly subscription' THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Assinatura_Mensal_Recorrente"""
        else:
            base_query = f"""
                SELECT
                    event_date AS Data,
                    traffic_category AS Cluster,
                    platform AS Plataforma,
                    city,
                    region,
                    country,
                    SUM(CASE WHEN event_name = 'paid_media' then value else 0 end) AS Investimento,
                    SUM(CASE WHEN event_name = 'paid_media' then clicks else 0 end) AS Cliques,
                    COUNTIF(event_name = 'session') AS Sessoes,
                    COUNTIF(event_name = 'add_to_cart') AS Adicoes_ao_Carrinho,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' then transaction_id end) AS Pedidos,
                    SUM(CASE WHEN event_name = '{attribution_model}' then value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) end) AS Receita,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') THEN transaction_id END) AS Pedidos_Pagos,
                    SUM(CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Paga,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') and transaction_no = 1 THEN transaction_id END) AS Novos_Clientes,
                    SUM(CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') and transaction_no = 1 THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Novos_Clientes,
                    -- Métricas de assinatura
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and order_type = 'first annual subscription' THEN transaction_id END) AS Pedidos_Assinatura_Anual_Inicial,
                    SUM(CASE WHEN event_name = '{attribution_model}' and order_type = 'first annual subscription' THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Assinatura_Anual_Inicial,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and order_type = 'first montly subscription' THEN transaction_id END) AS Pedidos_Assinatura_Mensal_Inicial,
                    SUM(CASE WHEN event_name = '{attribution_model}' and order_type = 'first montly subscription' THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Assinatura_Mensal_Inicial,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and order_type = 'recurring annual subscription' THEN transaction_id END) AS Pedidos_Assinatura_Anual_Recorrente,
                    SUM(CASE WHEN event_name = '{attribution_model}' and order_type = 'recurring annual subscription' THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Assinatura_Anual_Recorrente,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and order_type = 'recurring montly subscription' THEN transaction_id END) AS Pedidos_Assinatura_Mensal_Recorrente,
                    SUM(CASE WHEN event_name = '{attribution_model}' and order_type = 'recurring montly subscription' THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Assinatura_Mensal_Recorrente"""

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
        total_sessoes = 0
        # Totais para pedidos de assinatura
        total_pedidos_assinatura_anual_inicial = 0
        total_pedidos_assinatura_mensal_inicial = 0
        total_pedidos_assinatura_anual_recorrente = 0
        total_pedidos_assinatura_mensal_recorrente = 0
        
        for row in rows:
            # Função auxiliar para tratar valores NaN
            def safe_float(value):
                if value is None:
                    return 0.0
                try:
                    float_val = float(value)
                    return float_val if not math.isnan(float_val) else 0.0
                except (ValueError, TypeError):
                    return 0.0
            
            data_row = BasicDataRow(
                Data=str(row.Data),
                Cluster=str(row.Cluster) if row.Cluster else "Sem Categoria",
                Plataforma=str(row.Plataforma) if row.Plataforma else "",
                city=str(row.city) if hasattr(row, 'city') and row.city else "",
                region=str(row.region) if hasattr(row, 'region') and row.region else "",
                country=str(row.country) if hasattr(row, 'country') and row.country else "",
                Investimento=safe_float(row.Investimento),
                Cliques=int(row.Cliques or 0),
                Sessoes=int(row.Sessoes or 0),
                Adicoes_ao_Carrinho=int(row.Adicoes_ao_Carrinho or 0),
                Pedidos=int(row.Pedidos or 0),
                Receita=safe_float(row.Receita),
                Pedidos_Pagos=int(row.Pedidos_Pagos or 0),
                Receita_Paga=safe_float(row.Receita_Paga),
                Novos_Clientes=int(row.Novos_Clientes or 0),
                Receita_Novos_Clientes=safe_float(row.Receita_Novos_Clientes),
                # Novos campos de assinatura
                Pedidos_Assinatura_Anual_Inicial=int(row.Pedidos_Assinatura_Anual_Inicial) if hasattr(row, 'Pedidos_Assinatura_Anual_Inicial') and row.Pedidos_Assinatura_Anual_Inicial else 0,
                Receita_Assinatura_Anual_Inicial=safe_float(row.Receita_Assinatura_Anual_Inicial) if hasattr(row, 'Receita_Assinatura_Anual_Inicial') else 0.0,
                Pedidos_Assinatura_Mensal_Inicial=int(row.Pedidos_Assinatura_Mensal_Inicial) if hasattr(row, 'Pedidos_Assinatura_Mensal_Inicial') and row.Pedidos_Assinatura_Mensal_Inicial else 0,
                Receita_Assinatura_Mensal_Inicial=safe_float(row.Receita_Assinatura_Mensal_Inicial) if hasattr(row, 'Receita_Assinatura_Mensal_Inicial') else 0.0,
                Pedidos_Assinatura_Anual_Recorrente=int(row.Pedidos_Assinatura_Anual_Recorrente) if hasattr(row, 'Pedidos_Assinatura_Anual_Recorrente') and row.Pedidos_Assinatura_Anual_Recorrente else 0,
                Receita_Assinatura_Anual_Recorrente=safe_float(row.Receita_Assinatura_Anual_Recorrente) if hasattr(row, 'Receita_Assinatura_Anual_Recorrente') else 0.0,
                Pedidos_Assinatura_Mensal_Recorrente=int(row.Pedidos_Assinatura_Mensal_Recorrente) if hasattr(row, 'Pedidos_Assinatura_Mensal_Recorrente') and row.Pedidos_Assinatura_Mensal_Recorrente else 0,
                Receita_Assinatura_Mensal_Recorrente=safe_float(row.Receita_Assinatura_Mensal_Recorrente) if hasattr(row, 'Receita_Assinatura_Mensal_Recorrente') else 0.0
            )
            data.append(data_row)
            
            # Calcular totais
            total_investimento += data_row.Investimento
            total_receita += data_row.Receita
            total_pedidos += data_row.Pedidos
            total_sessoes += data_row.Sessoes
            # Calcular totais de assinatura
            total_pedidos_assinatura_anual_inicial += data_row.Pedidos_Assinatura_Anual_Inicial
            total_pedidos_assinatura_mensal_inicial += data_row.Pedidos_Assinatura_Mensal_Inicial
            total_pedidos_assinatura_anual_recorrente += data_row.Pedidos_Assinatura_Anual_Recorrente
            total_pedidos_assinatura_mensal_recorrente += data_row.Pedidos_Assinatura_Mensal_Recorrente
        
        # Calcular total geral de pedidos de assinatura
        total_pedidos_assinatura = (total_pedidos_assinatura_anual_inicial + 
                                   total_pedidos_assinatura_mensal_inicial + 
                                   total_pedidos_assinatura_anual_recorrente + 
                                   total_pedidos_assinatura_mensal_recorrente)
        
        # Criar resumo
        summary = {
            "total_investimento": total_investimento,
            "total_receita": total_receita,
            "total_pedidos": total_pedidos,
            "total_sessoes": total_sessoes,
            "total_pedidos_assinatura": total_pedidos_assinatura,
            "total_pedidos_assinatura_anual_inicial": total_pedidos_assinatura_anual_inicial,
            "total_pedidos_assinatura_mensal_inicial": total_pedidos_assinatura_mensal_inicial,
            "total_pedidos_assinatura_anual_recorrente": total_pedidos_assinatura_anual_recorrente,
            "total_pedidos_assinatura_mensal_recorrente": total_pedidos_assinatura_mensal_recorrente,
            "roas": total_receita / total_investimento if total_investimento > 0 else 0,
            "ticket_medio": total_receita / total_pedidos if total_pedidos > 0 else 0,
            "taxa_conversao": (total_pedidos / total_sessoes * 100) if total_sessoes > 0 else 0,
            "periodo": f"{start_date} a {end_date}",
            "tablename": tablename,
            "user_access": "all" if user_tablename == 'all' else "limited",
            "attribution_model": request.attribution_model
        }
        
        # Preparar resposta
        response_data = {
            'total_rows': len(data),
            'summary': summary,
            'data': [row.dict() for row in data],
            'cached_at': datetime.now().isoformat()
        }
        
        # Salvar último request
        last_request_manager.save_last_request(
            'basic-data',
            {
                'start_date': request.start_date,
                'end_date': request.end_date,
                'table_name': request.table_name,
                'attribution_model': request.attribution_model,
                'filters': request.filters
            },
            token.email
        )
        
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
    """Endpoint para buscar dados diários de métricas do funil de conversão com cache de 1 hora"""
    
    # Parâmetros para o cache
    cache_params = {
        'email': token.email,
        'start_date': request.start_date,
        'end_date': request.end_date,
        'table_name': request.table_name
    }
    
    # Tentar buscar do cache primeiro
    cached_data = daily_metrics_cache.get(**cache_params)
    if cached_data:
        return DailyMetricsResponse(
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
            event_date AS Data,
            view_item AS Visualizacao_de_Item,
            add_to_cart AS Adicionar_ao_Carrinho,
            begin_checkout AS Iniciar_Checkout,
            add_shipping_info AS Adicionar_Informacao_de_Frete,
            add_payment_info AS Adicionar_Informacao_de_Pagamento,
            purchase AS Pedido
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
        
        # Preparar resposta
        response_data = {
            'data': [row.dict() for row in data],
            'total_rows': len(data),
            'summary': summary,
            'cached_at': datetime.now().isoformat()
        }
        
        # Salvar último request
        last_request_manager.save_last_request(
            'daily-metrics',
            {
                'start_date': request.start_date,
                'end_date': request.end_date,
                'table_name': request.table_name
            },
            token.email
        )
        
        # Armazenar no cache
        daily_metrics_cache.set(response_data, **cache_params)
        
        return DailyMetricsResponse(
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
        print(f"Erro ao buscar dados diários de métricas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.post("/orders", response_model=OrdersResponse)
async def get_orders(
    request: OrdersRequest,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar orders detalhados com cache de 1 hora"""
    
    # Parâmetros para o cache
    cache_params = {
        'email': token.email,
        'start_date': request.start_date,
        'end_date': request.end_date,
        'table_name': request.table_name,
        'limit': request.limit,
        'offset': request.offset,
        'traffic_category': request.traffic_category,
        'fs_traffic_category': request.fs_traffic_category,
        'fsm_traffic_category': request.fsm_traffic_category
    }
    
    # Tentar buscar do cache primeiro
    cached_data = orders_cache.get(**cache_params)
    if cached_data:
        return OrdersResponse(
            data=cached_data['data'],
            total_rows=cached_data['total_rows'],
            summary=cached_data['summary']
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
        
        # Determinar projeto
        project_name = get_project_name(tablename)
        
        # Query de teste para verificar estrutura da tabela
        test_query = f"""
        SELECT *
        FROM `{project_name}.dbt_join.{tablename}_orders_sessions`
        WHERE date(created_at) BETWEEN '{request.start_date}' AND '{request.end_date}'
        LIMIT 1
        """
        
        print(f"=== TESTE: Verificando estrutura da tabela ===")
        print(f"Executando query de teste: {test_query}")
        
        test_result = client.query(test_query)
        test_rows = list(test_result.result())
        
        if test_rows:
            test_row = test_rows[0]
            print(f"Campos disponíveis na tabela: {list(test_row.keys())}")
            print(f"Primeira linha completa: {dict(test_row)}")
        else:
            print("Nenhum resultado encontrado na tabela")
        
        print(f"=== FIM DO TESTE ===")
        
        # Construir condições de filtro para traffic_category
        filter_conditions = [f"date(created_at) BETWEEN '{request.start_date}' AND '{request.end_date}'"]
        
        if request.traffic_category:
            filter_conditions.append(f"traffic_category = '{request.traffic_category}'")
        
        if request.fs_traffic_category:
            filter_conditions.append(f"fs_traffic_category = '{request.fs_traffic_category}'")
        
        if request.fsm_traffic_category:
            filter_conditions.append(f"fsm_traffic_category = '{request.fsm_traffic_category}'")
        
        where_clause = " AND ".join(filter_conditions)
        
        # Construir query para orders - corrigida com base na estrutura real da tabela
        query = f"""
        SELECT
            created_at as Horario,
            COALESCE(transaction_id, '') as ID_da_Transacao,
            COALESCE(first_name, '') as Primeiro_Nome,
            status as Status,
            value as Receita,
            source_name as Canal,
            
            COALESCE(traffic_category, '') as Categoria_de_Trafico,
            source as Origem,
            COALESCE(medium, '') as Midia,
            campaign as Campanha,
            COALESCE(content, '') as Conteudo,
            COALESCE(page_location, '') as Pagina_de_Entrada,
            COALESCE(page_params, '') as Parametros_de_URL,

            COALESCE(fs_traffic_category, '') as Categoria_de_Trafico_Primeiro_Clique,
            COALESCE(fs_source, '') as Origem_Primeiro_Clique,
            COALESCE(fs_medium, '') as Midia_Primeiro_Clique,
            COALESCE(fs_campaign, '') as Campanha_Primeiro_Clique,
            COALESCE(fs_content, '') as Conteudo_Primeiro_Clique,
            COALESCE(fs_page_location, '') as Pagina_de_Entrada_Primeiro_Clique,
            COALESCE(fs_page_params, '') as Parametros_de_URL_Primeiro_Clique,
            
            COALESCE(fsm_traffic_category, '') as Categoria_de_Trafico_Primeiro_Lead,
            COALESCE(fsm_source, '') as Origem_Primeiro_Lead,
            COALESCE(fsm_medium, '') as Midia_Primeiro_Lead,
            COALESCE(fsm_campaign, '') as Campanha_Primeiro_Lead,
            COALESCE(fsm_content, '') as Conteudo_Primeiro_Lead,
            COALESCE(fsm_page_location, '') as Pagina_de_Entrada_Primeiro_Lead,
            COALESCE(fsm_page_params, '') as Parametros_de_URL_Primeiro_Lead
            
        FROM `{project_name}.dbt_join.{tablename}_orders_sessions`
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT {request.limit}
        OFFSET {request.offset}
    """
        
        print(f"=== QUERY PRINCIPAL ===")
        print(f"Executando query principal: {query}")
        print(f"=== FIM QUERY PRINCIPAL ===")
        
        # Executar query
        result = client.query(query)
        rows = list(result.result())
        
        # Debug: mostrar campos disponíveis na primeira linha
        if rows:
            print(f"=== RESULTADOS DA QUERY PRINCIPAL ===")
            print(f"Total de linhas retornadas: {len(rows)}")
            if len(rows) > 0:
                first_row = rows[0]
                print(f"Campos disponíveis: {list(first_row.keys())}")
                print(f"Primeira linha: {dict(first_row)}")
            print(f"=== FIM RESULTADOS ===")
        
        # Converter para formato de resposta
        data = []
        total_receita = 0
        total_orders = 0
        
        for row in rows:
            try:
                # Usar getattr com valor padrão para evitar erros
                horario_value = getattr(row, 'Horario', '')
                # Converter datetime para string se necessário
                if hasattr(horario_value, 'isoformat'):
                    horario_value = horario_value.isoformat()
                elif horario_value is not None:
                    horario_value = str(horario_value)
                else:
                    horario_value = ''
                
                order_row = OrderRow(
                    Horario=horario_value,
                    ID_da_Transacao=str(getattr(row, 'ID_da_Transacao', '')),
                    Primeiro_Nome=str(getattr(row, 'Primeiro_Nome', '')),
                    Status=str(getattr(row, 'Status', '')),
                    Receita=float(getattr(row, 'Receita', 0) or 0),
                    Canal=str(getattr(row, 'Canal', '')),
                    
                    # Campos do último clique
                    Categoria_de_Trafico=str(getattr(row, 'Categoria_de_Trafico', '')),
                    Origem=str(getattr(row, 'Origem', '')),
                    Midia=str(getattr(row, 'Midia', '')),
                    Campanha=str(getattr(row, 'Campanha', '')),
                    Conteudo=str(getattr(row, 'Conteudo', '')),
                    Pagina_de_Entrada=str(getattr(row, 'Pagina_de_Entrada', '')),
                    Parametros_de_URL=str(getattr(row, 'Parametros_de_URL', '')),
                    
                    # Campos do primeiro clique
                    Categoria_de_Trafico_Primeiro_Clique=str(getattr(row, 'Categoria_de_Trafico_Primeiro_Clique', '')),
                    Origem_Primeiro_Clique=str(getattr(row, 'Origem_Primeiro_Clique', '')),
                    Midia_Primeiro_Clique=str(getattr(row, 'Midia_Primeiro_Clique', '')),
                    Campanha_Primeiro_Clique=str(getattr(row, 'Campanha_Primeiro_Clique', '')),
                    Conteudo_Primeiro_Clique=str(getattr(row, 'Conteudo_Primeiro_Clique', '')),
                    Pagina_de_Entrada_Primeiro_Clique=str(getattr(row, 'Pagina_de_Entrada_Primeiro_Clique', '')),
                    Parametros_de_URL_Primeiro_Clique=str(getattr(row, 'Parametros_de_URL_Primeiro_Clique', '')),
                    
                    # Campos do primeiro lead
                    Categoria_de_Trafico_Primeiro_Lead=str(getattr(row, 'Categoria_de_Trafico_Primeiro_Lead', '')),
                    Origem_Primeiro_Lead=str(getattr(row, 'Origem_Primeiro_Lead', '')),
                    Midia_Primeiro_Lead=str(getattr(row, 'Midia_Primeiro_Lead', '')),
                    Campanha_Primeiro_Lead=str(getattr(row, 'Campanha_Primeiro_Lead', '')),
                    Conteudo_Primeiro_Lead=str(getattr(row, 'Conteudo_Primeiro_Lead', '')),
                    Pagina_de_Entrada_Primeiro_Lead=str(getattr(row, 'Pagina_de_Entrada_Primeiro_Lead', '')),
                    Parametros_de_URL_Primeiro_Lead=str(getattr(row, 'Parametros_de_URL_Primeiro_Lead', ''))
                )
            except Exception as e:
                print(f"Erro ao processar linha: {e}")
                print(f"Tipo do objeto row: {type(row)}")
                print(f"Atributos disponíveis: {dir(row)}")
                if hasattr(row, '__dict__'):
                    print(f"Dict do objeto: {row.__dict__}")
                print(f"Campos disponíveis na linha: {list(row.keys()) if hasattr(row, 'keys') else 'N/A'}")
                raise
            data.append(order_row)
            
            # Calcular totais
            total_receita += order_row.Receita
            total_orders += 1
        
        # Criar resumo
        summary = {
            "total_orders": total_orders,
            "total_revenue": total_receita,
            "average_order_value": total_receita / total_orders if total_orders > 0 else 0,
            "period": f"{request.start_date} a {request.end_date}",
            "table_name": tablename,
            "filters_applied": {
                "traffic_category": request.traffic_category,
                "fs_traffic_category": request.fs_traffic_category,
                "fsm_traffic_category": request.fsm_traffic_category
            }
        }
        
        # Preparar resposta
        response_data = {
            'data': [row.dict() for row in data],
            'total_rows': len(data),
            'summary': summary,
            'cached_at': datetime.now().isoformat()
        }
        
        # Salvar último request
        last_request_manager.save_last_request(
            'orders',
            {
                'start_date': request.start_date,
                'end_date': request.end_date,
                'table_name': request.table_name,
                'limit': request.limit,
                'offset': request.offset,
                'traffic_category': request.traffic_category,
                'fs_traffic_category': request.fs_traffic_category,
                'fsm_traffic_category': request.fsm_traffic_category
            },
            token.email
        )
        
        # Armazenar no cache
        orders_cache.set(response_data, **cache_params)
        
        return OrdersResponse(
            data=data,
            total_rows=len(data),
            summary=summary
        )
        
    except Exception as e:
        print(f"Erro ao buscar orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )




@metrics_router.post("/goals", response_model=UserGoalsResponse)
async def get_user_goals(
    request: UserGoalsRequest,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar metas do usuário"""
    
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        # Buscar informações do usuário para verificar permissões
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
        
        # Verificar permissões para acessar a tabela solicitada
        if user_tablename == 'all':
            # Usuário com acesso total pode acessar qualquer tabela
            tablename = request.table_name
            print(f"🔓 Usuário com acesso total acessando metas da tabela: {tablename}")
        else:
            # Usuário com acesso limitado só pode acessar sua própria tabela
            if request.table_name != user_tablename:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode acessar metas da tabela '{request.table_name}'"
                )
            tablename = request.table_name
            print(f"🔒 Usuário com acesso limitado acessando metas da tabela: {tablename}")

        # Query para buscar metas do usuário
        goals_query = f"""
        SELECT goals
        FROM `mymetric-hub-shopify.dbt_config.user_goals`
        WHERE username = '{tablename}'
        LIMIT 1
        """
        
        print(f"Executando query de metas: {goals_query}")
        
        # Executar query
        goals_result = client.query(goals_query)
        goals_data = list(goals_result.result())
        
        if not goals_data:
            # Se não encontrar metas, retornar metas padrão
            default_goals = {
                "revenue_goal": 100000.0,
                "orders_goal": 1000,
                "conversion_rate_goal": 5.0,
                "roas_goal": 8.0,
                "new_customers_goal": 100
            }
            
            # Salvar último request
            last_request_manager.save_last_request(
                'goals',
                {
                    'table_name': request.table_name
                },
                token.email
            )
            
            return UserGoalsResponse(
                username=tablename,
                goals=default_goals,
                message="Metas padrão aplicadas (nenhuma meta configurada encontrada)"
            )
        
        # Processar metas encontradas
        goals = goals_data[0].goals
        
        # Se goals for string JSON, converter para dict
        if isinstance(goals, str):
            import json
            try:
                goals = json.loads(goals)
            except json.JSONDecodeError:
                goals = {}
        
        # Se goals for None ou vazio, usar metas padrão
        if not goals:
            goals = {
                "revenue_goal": 100000.0,
                "orders_goal": 1000,
                "conversion_rate_goal": 5.0,
                "roas_goal": 8.0,
                "new_customers_goal": 100
            }
        
        # Salvar último request
        last_request_manager.save_last_request(
            'goals',
            {
                'table_name': request.table_name
            },
            token.email
        )
        
        return UserGoalsResponse(
            username=tablename,
            goals=goals,
            message="Metas carregadas com sucesso"
        )
        
    except Exception as e:
        print(f"Erro ao buscar metas do usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.post("/detailed-data", response_model=DetailedDataResponse)
async def get_detailed_data(
    request: DetailedDataRequest,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar dados detalhados com métricas agregadas e cache de 1 hora"""
    
    # Validar limites de paginação primeiro
    limit = min(request.limit or 10000, 50000)  # Máximo 50000 registros
    offset = max(request.offset or 0, 0)      # Offset não pode ser negativo
    
    if request.limit and request.limit > 50000:
        print(f"⚠️ Limite muito alto ({request.limit}), usando máximo de 50000")
    if request.offset and request.offset < 0:
        print(f"⚠️ Offset negativo ({request.offset}), usando 0")
    
    # Validar campo de ordenação
    valid_order_fields = ['Pedidos', 'Receita', 'Sessoes', 'Adicoes_ao_Carrinho', 'Data', 'Hora']
    order_by = request.order_by or 'Pedidos'
    if order_by not in valid_order_fields:
        order_by = 'Pedidos'
        print(f"⚠️ Campo de ordenação '{request.order_by}' inválido, usando 'Pedidos'")
    
    # Verificar cache primeiro
    cache_params = {
        'email': token.email, 
        'start_date': request.start_date, 
        'end_date': request.end_date, 
        'table_name': request.table_name,
        'attribution_model': request.attribution_model,
        'limit': limit,
        'offset': offset,
        'order_by': order_by
    }
    
    cached_data = detailed_data_cache.get(**cache_params)
    if cached_data:
        return DetailedDataResponse(
            data=cached_data['data'], 
            total_rows=cached_data['total_rows'], 
            summary=cached_data['summary'],
            cache_info={'source': 'cache', 'cached_at': cached_data.get('cached_at'), 'ttl_hours': 4},
            pagination={
                'limit': limit,
                'offset': offset,
                'order_by': order_by,
                'has_more': len(cached_data['data']) == limit
            }
        )
    
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
        
        # Determinar qual tabela usar
        if user_tablename == 'all':
            if request.table_name:
                tablename = request.table_name
            else:
                tablename = 'constance'
        else:
            if request.table_name and request.table_name != user_tablename:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode acessar '{request.table_name}'"
                )
            tablename = user_tablename
        
        # Determinar projeto
        project_name = get_project_name(tablename)
        
        # Processar modelo de atribuição (igual ao basic-data)
        attribution_model = request.attribution_model or 'Último Clique Não Direto'
        
        print(f"🔍 Modelo de atribuição original: {attribution_model}")
        
        if attribution_model == 'Último Clique Não Direto':
            attribution_model = 'purchase'
            print("🔄 Convertido 'Último Clique Não Direto' para 'purchase'")
        elif attribution_model == 'Primeiro Clique':
            attribution_model = 'fs_purchase'
            print("🔄 Convertido 'Primeiro Clique' para 'fs_purchase'")
        elif attribution_model == 'Assinaturas' and tablename == 'coffeemais':
            attribution_model = 'purchase_subscription'
            print("🔄 Convertido 'Assinaturas' para 'purchase_subscription'")
        
        print(f"🔍 Modelo de atribuição convertido: {attribution_model}")
        print(f"🔍 Usando na query: event_name = '{attribution_model}'")
        
        # Construir condição de data
        date_condition = f"event_date BETWEEN '{request.start_date}' AND '{request.end_date}'"
        
        # Query que agrega TODAS as métricas juntas (não usa UNION ALL)
        query = f"""
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
            COUNTIF(event_name = 'session') as `Sessoes`,
            COUNTIF(event_name = 'add_to_cart') as `Adicoes_ao_Carrinho`,
            COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' THEN transaction_id END) as `Pedidos`,
            SUM(CASE WHEN event_name = '{attribution_model}' THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) as `Receita`,
            COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' AND status in ('paid', 'authorized') THEN transaction_id END) as `Pedidos_Pagos`,
            SUM(CASE WHEN event_name = '{attribution_model}' AND status in ('paid', 'authorized') THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) as `Receita_Paga`
        FROM `{project_name}.dbt_join.{tablename}_events_long`
        WHERE {date_condition}
        GROUP BY event_date, extract(hour from created_at), source, medium, campaign, page_location, content, discount_code, traffic_category
        ORDER BY {order_by} DESC
        LIMIT {limit} OFFSET {offset}
        """
        
        print(f"Executando query de dados detalhados com paginação: limit={limit}, offset={offset}, order_by={order_by}")
        
        # Executar query
        result = client.query(query)
        rows = list(result.result())
        
        # Calcular sumário com base nos mesmos grupos, SEM paginação
        summary_query = f"""
        SELECT
            SUM(Sessoes) as total_sessions,
            SUM(Adicoes_ao_Carrinho) as total_add_to_cart,
            SUM(Pedidos) as total_orders,
            SUM(Receita) as total_revenue,
            SUM(Pedidos_Pagos) as total_paid_orders,
            SUM(Receita_Paga) as total_paid_revenue
        FROM (
            SELECT
                COUNTIF(event_name = 'session') as Sessoes,
                COUNTIF(event_name = 'add_to_cart') as Adicoes_ao_Carrinho,
                COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' THEN transaction_id END) as Pedidos,
                SUM(CASE WHEN event_name = '{attribution_model}' THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) as Receita,
                COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' AND status in ('paid', 'authorized') THEN transaction_id END) as Pedidos_Pagos,
                SUM(CASE WHEN event_name = '{attribution_model}' AND status in ('paid', 'authorized') THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) as Receita_Paga
            FROM `{project_name}.dbt_join.{tablename}_events_long`
            WHERE {date_condition}
            GROUP BY event_date, extract(hour from created_at), source, medium, campaign, page_location, content, discount_code, traffic_category
        )
        """
        
        print(f"🔍 Executando query de sumário...")
        summary_result = client.query(summary_query)
        summary_row = list(summary_result.result())[0]
        
        # Extrair valores do sumário
        total_sessions = int(summary_row.total_sessions) if summary_row.total_sessions else 0
        total_add_to_cart = int(summary_row.total_add_to_cart) if summary_row.total_add_to_cart else 0
        total_orders = int(summary_row.total_orders) if summary_row.total_orders else 0
        total_revenue = float(summary_row.total_revenue) if summary_row.total_revenue else 0.0
        total_paid_orders = int(summary_row.total_paid_orders) if summary_row.total_paid_orders else 0
        total_paid_revenue = float(summary_row.total_paid_revenue) if summary_row.total_paid_revenue else 0.0
        
        # Calcular métricas derivadas
        conversion_rate = (total_orders / total_sessions * 100) if total_sessions > 0 else 0
        add_to_cart_rate = (total_add_to_cart / total_sessions * 100) if total_sessions > 0 else 0
        ticket_medio = total_revenue / total_orders if total_orders > 0 else 0
        ticket_medio_pago = total_paid_revenue / total_paid_orders if total_paid_orders > 0 else 0
        
        # Criar sumário completo
        summary = {
            # Totais principais
            "total_sessoes": total_sessions,
            "total_adicoes_carrinho": total_add_to_cart,
            "total_pedidos": total_orders,
            "total_receita": round(total_revenue, 2),
            "total_pedidos_pagos": total_paid_orders,
            "total_receita_paga": round(total_paid_revenue, 2),
            
            # Taxas de conversão
            "taxa_conversao": round(conversion_rate, 2),
            "taxa_adicao_carrinho": round(add_to_cart_rate, 2),
            "taxa_checkout": round((total_orders / total_add_to_cart * 100) if total_add_to_cart > 0 else 0, 2),
            
            # Ticket médio
            "ticket_medio": round(ticket_medio, 2),
            "ticket_medio_pago": round(ticket_medio_pago, 2),
            
            # Informações contextuais
            "periodo": f"{request.start_date} a {request.end_date}",
            "tablename": tablename,
            "project_name": project_name,
            "attribution_model": request.attribution_model,
            "user_access": "all" if user_tablename == 'all' else "limited"
        }
        
        print(f"✅ Sumário calculado: {total_sessions} sessões, {total_orders} pedidos, R$ {total_revenue:.2f} receita")
        
        # Processar resultados paginados
        data = []
        data = []
        
        for row in rows:
            data.append(DetailedDataRow(
                Data=str(row.Data),
                Hora=int(row.Hora) if row.Hora else 0,
                Origem=str(row.Origem) if row.Origem else '',
                Midia=str(row.Midia) if row.Midia else '',
                Campanha=str(row.Campanha) if row.Campanha else '',
                Pagina_de_Entrada=str(row.Pagina_de_Entrada) if row.Pagina_de_Entrada else '',
                Conteudo=str(row.Conteudo) if row.Conteudo else '',
                Cupom=str(row.Cupom) if row.Cupom else '',
                Cluster=str(row.Cluster) if row.Cluster else '',
                Sessoes=int(row.Sessoes) if row.Sessoes else 0,
                Adicoes_ao_Carrinho=int(row.Adicoes_ao_Carrinho) if row.Adicoes_ao_Carrinho else 0,
                Pedidos=int(row.Pedidos) if row.Pedidos else 0,
                Receita=float(row.Receita) if row.Receita else 0.0,
                Pedidos_Pagos=int(row.Pedidos_Pagos) if row.Pedidos_Pagos else 0,
                Receita_Paga=float(row.Receita_Paga) if row.Receita_Paga else 0.0
            ))
        
        # Salvar último request
        last_request_manager.save_last_request(
            'detailed-data',
            {
                'start_date': request.start_date,
                'end_date': request.end_date,
                'table_name': request.table_name,
                'attribution_model': request.attribution_model,
                'limit': limit,
                'offset': offset,
                'order_by': order_by
            },
            token.email
        )
        
        # Preparar dados para cache
        response_data = {
            'data': [row.dict() for row in data],
            'total_rows': len(data),
            'summary': summary,
            'cached_at': datetime.now().isoformat()
        }
        
        # Salvar no cache
        detailed_data_cache.set(response_data, **cache_params)
        
        return DetailedDataResponse(
            data=data,
            total_rows=len(data),
            summary=summary,
            cache_info={'source': 'database', 'cached_at': response_data['cached_at'], 'ttl_hours': 4},
            pagination={
                'limit': limit,
                'offset': offset,
                'order_by': order_by,
                'has_more': len(data) == limit
            }
        )
        
    except Exception as e:
        print(f"Erro ao buscar dados detalhados: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.post("/product-trend", response_model=ProductTrendResponse)
async def get_product_trend(
    request: ProductTrendRequest,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar dados de tendência de produtos com paginação"""
    
    # Validar limites de paginação
    limit = min(request.limit or 100, 1000)  # Máximo 1000 registros
    offset = max(request.offset or 0, 0)      # Offset não pode ser negativo
    
    if request.limit and request.limit > 1000:
        print(f"⚠️ Limite muito alto ({request.limit}), usando máximo de 1000")
    if request.offset and request.offset < 0:
        print(f"⚠️ Offset negativo ({request.offset}), usando 0")
    
    # Validar campo de ordenação
    valid_order_fields = ['purchases_week_4', 'purchases_week_3', 'purchases_week_2', 'purchases_week_1', 
                         'percent_change_w3_w4', 'percent_change_w2_w3', 'percent_change_w1_w2', 
                         'item_name', 'trend_status', 'benchmark_week_1', 'benchmark_week_2', 
                         'benchmark_week_3', 'benchmark_week_4', 'clicks_week_1', 'clicks_week_2',
                         'clicks_week_3', 'clicks_week_4', 'size_score_week_4', 'size_score_week_3', 
                         'size_score_week_2', 'size_score_week_1', 'size_score_trend_status']
    order_by = request.order_by or 'purchases_week_4'
    if order_by not in valid_order_fields:
        order_by = 'purchases_week_4'
        print(f"⚠️ Campo de ordenação '{request.order_by}' inválido, usando 'purchases_week_4'")
    
    # Parâmetros para o cache
    cache_params = {
        'email': token.email,
        'table_name': request.table_name,
        'limit': limit,
        'offset': offset,
        'order_by': order_by
    }
    
    # Tentar buscar do cache primeiro
    cached_data = product_trend_cache.get(**cache_params)
    if cached_data:
        return ProductTrendResponse(
            data=cached_data['data'],
            total_rows=cached_data['total_rows'],
            summary=cached_data['summary'],
            cache_info={
                'source': 'cache',
                'cached_at': cached_data.get('cached_at'),
                'ttl_hours': 2
            },
            pagination={
                'limit': limit,
                'offset': offset,
                'order_by': order_by,
                'has_more': len(cached_data['data']) == limit
            }
        )
    
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
        
        # Determinar qual tabela usar
        if user_tablename == 'all':
            # Usuário tem acesso a todas as tabelas
            tablename = request.table_name
            print(f"🔓 Usuário com acesso total acessando tabela: {tablename}")
        else:
            # Usuário tem acesso limitado a uma tabela específica
            if request.table_name != user_tablename:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode acessar '{request.table_name}'"
                )
            tablename = request.table_name
            print(f"🔒 Usuário com acesso limitado usando tabela: {tablename}")

        # Determinar projeto
        project_name = get_project_name(tablename)
        
        # Verificar quais campos benchmark e clicks existem na tabela
        benchmark_fields = []
        clicks_fields = []
        fields_check_query = f"""
        SELECT column_name
        FROM `{project_name}.dbt_aggregated.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = '{tablename}_product_trend'
        AND (column_name LIKE 'benchmark_week_%' OR column_name LIKE 'clicks_week_%')
        ORDER BY column_name
        """
        
        try:
            fields_result = client.query(fields_check_query)
            fields_rows = list(fields_result.result())
            all_extra_fields = [row.column_name for row in fields_rows]
            
            benchmark_fields = [field for field in all_extra_fields if field.startswith('benchmark_week_')]
            clicks_fields = [field for field in all_extra_fields if field.startswith('clicks_week_')]
            
            print(f"Campos benchmark encontrados para {tablename}: {benchmark_fields}")
            print(f"Campos clicks encontrados para {tablename}: {clicks_fields}")
        except Exception as e:
            print(f"Aviso: Não foi possível verificar campos extras para {tablename}: {e}")
            benchmark_fields = []
            clicks_fields = []
        
        # Query para buscar dados de tendência de produtos com paginação
        # Incluir campos específicos do Havaianas se necessário
        # Construir query base
        base_fields = [
            "item_id",
            "item_name", 
            "purchases_week_1",
            "purchases_week_2",
            "purchases_week_3",
            "purchases_week_4",
            "percent_change_w1_w2",
            "percent_change_w2_w3",
            "percent_change_w3_w4",
            "trend_status",
            "trend_consistency"
        ]
        
        # Adicionar campos benchmark e clicks se existirem
        all_fields = base_fields + benchmark_fields + clicks_fields
        
        # Adicionar campos específicos do Havaianas se for a tabela havaianas
        if tablename == 'havaianas':
            havaianas_fields = [
                "size_score_week_1",
                "size_score_week_2", 
                "size_score_week_3",
                "size_score_week_4",
                "size_score_trend_status"
            ]
            all_fields.extend(havaianas_fields)
        
        # Construir query final
        fields_str = ",\n                ".join(all_fields)
        query = f"""
        SELECT
                {fields_str}
        FROM `{project_name}.dbt_aggregated.{tablename}_product_trend`
        ORDER BY {order_by} DESC
        LIMIT {limit}
        OFFSET {offset}
        """
        
        print(f"Executando query product-trend: {query}")
        
        # Executar query
        result = client.query(query)
        rows = list(result.result())
        
        # Converter para formato de resposta
        data = []
        total_products = 0
        total_purchases_w4 = 0
        
        for row in rows:
            # Construir objeto base
            data_row_data = {
                'item_id': str(row.item_id) if row.item_id else "",
                'item_name': str(row.item_name) if row.item_name else "",
                'purchases_week_1': int(row.purchases_week_1) if row.purchases_week_1 is not None else 0,
                'purchases_week_2': int(row.purchases_week_2) if row.purchases_week_2 is not None else 0,
                'purchases_week_3': int(row.purchases_week_3) if row.purchases_week_3 is not None else 0,
                'purchases_week_4': int(row.purchases_week_4) if row.purchases_week_4 is not None else 0,
                'percent_change_w1_w2': float(row.percent_change_w1_w2) if row.percent_change_w1_w2 is not None else 0.0,
                'percent_change_w2_w3': float(row.percent_change_w2_w3) if row.percent_change_w2_w3 is not None else 0.0,
                'percent_change_w3_w4': float(row.percent_change_w3_w4) if row.percent_change_w3_w4 is not None else 0.0,
                'trend_status': str(row.trend_status) if row.trend_status else "",
                'trend_consistency': str(row.trend_consistency) if row.trend_consistency else "",
                'benchmark_week_1': None,
                'benchmark_week_2': None,
                'benchmark_week_3': None,
                'benchmark_week_4': None,
                'clicks_week_1': None,
                'clicks_week_2': None,
                'clicks_week_3': None,
                'clicks_week_4': None
            }
            
            # Adicionar campos benchmark se existirem na tabela
            for field in benchmark_fields:
                if hasattr(row, field):
                    data_row_data[field] = float(getattr(row, field)) if getattr(row, field) is not None else None
            
            # Adicionar campos clicks se existirem na tabela
            for field in clicks_fields:
                if hasattr(row, field):
                    data_row_data[field] = int(getattr(row, field)) if getattr(row, field) is not None else None
            
            # Adicionar campos específicos do Havaianas se disponíveis
            if tablename == 'havaianas' and hasattr(row, 'size_score_week_1'):
                data_row_data.update({
                    'size_score_week_1': float(row.size_score_week_1) if row.size_score_week_1 is not None else None,
                    'size_score_week_2': float(row.size_score_week_2) if row.size_score_week_2 is not None else None,
                    'size_score_week_3': float(row.size_score_week_3) if row.size_score_week_3 is not None else None,
                    'size_score_week_4': float(row.size_score_week_4) if row.size_score_week_4 is not None else None,
                    'size_score_trend_status': str(row.size_score_trend_status) if row.size_score_trend_status else None
                })
            
            data_row = ProductTrendRow(**data_row_data)
            data.append(data_row)
            
            # Calcular totais
            total_products += 1
            total_purchases_w4 += data_row.purchases_week_4
        
        # Criar resumo
        summary = {
            "total_products": total_products,
            "total_purchases_week_4": total_purchases_w4,
            "average_purchases_week_4": total_purchases_w4 / total_products if total_products > 0 else 0,
            "table_name": tablename,
            "project_name": project_name,
            "limit_applied": limit,
            "offset_applied": offset,
            "order_by_applied": order_by
        }
        
        # Preparar dados para cache
        response_data = {
            'data': [row.dict() for row in data],
            'total_rows': len(data),
            'summary': summary,
            'cached_at': datetime.now().isoformat()
        }
        
        # Salvar último request
        last_request_manager.save_last_request(
            'product-trend',
            {
                'table_name': request.table_name,
                'limit': limit,
                'offset': offset,
                'order_by': order_by
            },
            token.email
        )
        
        # Armazenar no cache
        product_trend_cache.set(response_data, **cache_params)
        
        return ProductTrendResponse(
            data=data,
            total_rows=len(data),
            summary=summary,
            cache_info={
                'source': 'database',
                'cached_at': response_data['cached_at'],
                'ttl_hours': 2
            },
            pagination={
                'limit': limit,
                'offset': offset,
                'order_by': order_by,
                'has_more': len(data) == limit
            }
        )
        
    except Exception as e:
        print(f"Erro ao buscar dados de tendência de produtos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.post("/ads-campaigns-results", response_model=AdsCampaignsResultsResponse)
async def get_ads_campaigns_results(
    request: AdsCampaignsResultsRequest,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar dados de resultados de campanhas publicitárias com cache de 2 horas"""
    
    # Se last_cache for True, buscar o último request salvo específico por table_name
    if request.last_cache:
        if not request.table_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="table_name é obrigatório quando last_cache é true"
            )
        
        last_request = last_request_manager.get_last_request('ads-campaigns-results', request.table_name)
        if last_request:
            # Executar o último request salvo (se o usuário tem acesso à tabela, pode ver requests de qualquer usuário)
            return await execute_last_request('ads-campaigns-results', last_request['request_data'], token)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhum último request encontrado para a tabela '{request.table_name}'"
            )
    
    # Validação para request normal (quando last_cache é false)
    if not request.last_cache:
        if not request.start_date or not request.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date e end_date são obrigatórios quando last_cache é false"
            )
    
    # Parâmetros para o cache
    cache_params = {
        'email': token.email,
        'start_date': request.start_date,
        'end_date': request.end_date,
        'table_name': request.table_name
    }
    
    # Tentar buscar do cache primeiro (apenas se force_refresh for False)
    if not request.force_refresh:
        cached_data = ads_campaigns_results_cache.get(**cache_params)
        if cached_data:
            return AdsCampaignsResultsResponse(
                data=cached_data['data'],
                total_rows=cached_data['total_rows'],
                summary=cached_data['summary'],
                cache_info={
                    'source': 'cache',
                    'cached_at': cached_data.get('cached_at'),
                    'ttl_hours': 168  # 7 dias
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

        # Determinar projeto
        project_name = get_project_name(tablename)
        
        # Construir query baseada na SQL fornecida
        start_date_str = request.start_date
        end_date_str = request.end_date
        
        query = f"""
        SELECT
            platform,
            campaign_name,
            date,
            sum(cost) cost,
            sum(impressions) impressions,
            sum(clicks) clicks,
            sum(leads) Leads,
            sum(transactions) transactions,
            sum(revenue) revenue,
            sum(first_transaction) transactions_first,
            sum(first_revenue) revenue_first,
            sum(fsm_transactions) transactions_origin_stack,
            sum(fsm_revenue) revenue_origin_stack,
            sum(fsm_first_transaction) transactions_first_origin_stack,
            sum(fsm_first_revenue) revenue_first_origin_stack,
            -- Novas métricas de assinatura
            sum(first_montly_subscriptions) first_montly_subscriptions,
            sum(first_annual_subscriptions) first_annual_subscriptions,
            sum(recurring_montly_subscriptions) recurring_montly_subscriptions,
            sum(recurring_annual_subscriptions) recurring_annual_subscriptions,
            sum(first_montly_revenue) first_montly_revenue,
            sum(first_annual_revenue) first_annual_revenue,
            sum(recurring_montly_revenue) recurring_montly_revenue,
            sum(recurring_annual_revenue) recurring_annual_revenue,
            sum(fsm_first_montly_subscriptions) fsm_first_montly_subscriptions,
            sum(fsm_first_annual_subscriptions) fsm_first_annual_subscriptions,
            sum(fsm_recurring_montly_subscriptions) fsm_recurring_montly_subscriptions,
            sum(fsm_recurring_annual_subscriptions) fsm_recurring_annual_subscriptions,
            sum(fsm_first_montly_revenue) fsm_first_montly_revenue,
            sum(fsm_first_annual_revenue) fsm_first_annual_revenue,
            sum(fsm_recurring_montly_revenue) fsm_recurring_montly_revenue,
            sum(fsm_recurring_annual_revenue) fsm_recurring_annual_revenue
        FROM `{project_name}.dbt_join.{tablename}_ads_campaigns_results`
        WHERE date BETWEEN '{start_date_str}' AND '{end_date_str}'
        GROUP BY ALL
        ORDER BY cost DESC
        """
        
        print(f"Executando query ads-campaigns-results: {query}")
        
        # Executar query
        result = client.query(query)
        rows = list(result.result())
        
        # Converter para formato de resposta
        data = []
        total_cost = 0
        total_revenue = 0
        total_impressions = 0
        total_clicks = 0
        total_leads = 0
        total_transactions = 0
        # Totais para métricas de assinatura
        total_first_montly_subscriptions = 0
        total_first_annual_subscriptions = 0
        total_recurring_montly_subscriptions = 0
        total_recurring_annual_subscriptions = 0
        total_first_montly_revenue = 0.0
        total_first_annual_revenue = 0.0
        total_recurring_montly_revenue = 0.0
        total_recurring_annual_revenue = 0.0
        total_fsm_first_montly_subscriptions = 0
        total_fsm_first_annual_subscriptions = 0
        total_fsm_recurring_montly_subscriptions = 0
        total_fsm_recurring_annual_subscriptions = 0
        total_fsm_first_montly_revenue = 0.0
        total_fsm_first_annual_revenue = 0.0
        total_fsm_recurring_montly_revenue = 0.0
        total_fsm_recurring_annual_revenue = 0.0
        
        for row in rows:
            data_row = AdsCampaignsResultsRow(
                platform=str(row.platform) if row.platform else "",
                campaign_name=str(row.campaign_name) if row.campaign_name else "",
                date=str(row.date) if row.date else "",
                cost=float(row.cost) if row.cost else 0.0,
                impressions=int(row.impressions) if row.impressions else 0,
                clicks=int(row.clicks) if row.clicks else 0,
                leads=int(row.Leads) if row.Leads else 0,
                transactions=int(row.transactions) if row.transactions else 0,
                revenue=float(row.revenue) if row.revenue else 0.0,
                transactions_first=int(row.transactions_first) if row.transactions_first else 0,
                revenue_first=float(row.revenue_first) if row.revenue_first else 0.0,
                transactions_origin_stack=int(row.transactions_origin_stack) if row.transactions_origin_stack else 0,
                revenue_origin_stack=float(row.revenue_origin_stack) if row.revenue_origin_stack else 0.0,
                transactions_first_origin_stack=int(row.transactions_first_origin_stack) if row.transactions_first_origin_stack else 0,
                revenue_first_origin_stack=float(row.revenue_first_origin_stack) if row.revenue_first_origin_stack else 0.0,
                # Novos campos de assinatura
                first_montly_subscriptions=int(row.first_montly_subscriptions) if hasattr(row, 'first_montly_subscriptions') and row.first_montly_subscriptions else 0,
                first_annual_subscriptions=int(row.first_annual_subscriptions) if hasattr(row, 'first_annual_subscriptions') and row.first_annual_subscriptions else 0,
                recurring_montly_subscriptions=int(row.recurring_montly_subscriptions) if hasattr(row, 'recurring_montly_subscriptions') and row.recurring_montly_subscriptions else 0,
                recurring_annual_subscriptions=int(row.recurring_annual_subscriptions) if hasattr(row, 'recurring_annual_subscriptions') and row.recurring_annual_subscriptions else 0,
                first_montly_revenue=float(row.first_montly_revenue) if hasattr(row, 'first_montly_revenue') and row.first_montly_revenue else 0.0,
                first_annual_revenue=float(row.first_annual_revenue) if hasattr(row, 'first_annual_revenue') and row.first_annual_revenue else 0.0,
                recurring_montly_revenue=float(row.recurring_montly_revenue) if hasattr(row, 'recurring_montly_revenue') and row.recurring_montly_revenue else 0.0,
                recurring_annual_revenue=float(row.recurring_annual_revenue) if hasattr(row, 'recurring_annual_revenue') and row.recurring_annual_revenue else 0.0,
                fsm_first_montly_subscriptions=int(row.fsm_first_montly_subscriptions) if hasattr(row, 'fsm_first_montly_subscriptions') and row.fsm_first_montly_subscriptions else 0,
                fsm_first_annual_subscriptions=int(row.fsm_first_annual_subscriptions) if hasattr(row, 'fsm_first_annual_subscriptions') and row.fsm_first_annual_subscriptions else 0,
                fsm_recurring_montly_subscriptions=int(row.fsm_recurring_montly_subscriptions) if hasattr(row, 'fsm_recurring_montly_subscriptions') and row.fsm_recurring_montly_subscriptions else 0,
                fsm_recurring_annual_subscriptions=int(row.fsm_recurring_annual_subscriptions) if hasattr(row, 'fsm_recurring_annual_subscriptions') and row.fsm_recurring_annual_subscriptions else 0,
                fsm_first_montly_revenue=float(row.fsm_first_montly_revenue) if hasattr(row, 'fsm_first_montly_revenue') and row.fsm_first_montly_revenue else 0.0,
                fsm_first_annual_revenue=float(row.fsm_first_annual_revenue) if hasattr(row, 'fsm_first_annual_revenue') and row.fsm_first_annual_revenue else 0.0,
                fsm_recurring_montly_revenue=float(row.fsm_recurring_montly_revenue) if hasattr(row, 'fsm_recurring_montly_revenue') and row.fsm_recurring_montly_revenue else 0.0,
                fsm_recurring_annual_revenue=float(row.fsm_recurring_annual_revenue) if hasattr(row, 'fsm_recurring_annual_revenue') and row.fsm_recurring_annual_revenue else 0.0
            )
            data.append(data_row)
            
            # Calcular totais
            total_cost += data_row.cost
            total_revenue += data_row.revenue
            total_impressions += data_row.impressions
            total_clicks += data_row.clicks
            total_leads += data_row.leads
            total_transactions += data_row.transactions
            # Calcular totais de assinatura
            total_first_montly_subscriptions += data_row.first_montly_subscriptions
            total_first_annual_subscriptions += data_row.first_annual_subscriptions
            total_recurring_montly_subscriptions += data_row.recurring_montly_subscriptions
            total_recurring_annual_subscriptions += data_row.recurring_annual_subscriptions
            total_first_montly_revenue += data_row.first_montly_revenue
            total_first_annual_revenue += data_row.first_annual_revenue
            total_recurring_montly_revenue += data_row.recurring_montly_revenue
            total_recurring_annual_revenue += data_row.recurring_annual_revenue
            total_fsm_first_montly_subscriptions += data_row.fsm_first_montly_subscriptions
            total_fsm_first_annual_subscriptions += data_row.fsm_first_annual_subscriptions
            total_fsm_recurring_montly_subscriptions += data_row.fsm_recurring_montly_subscriptions
            total_fsm_recurring_annual_subscriptions += data_row.fsm_recurring_annual_subscriptions
            total_fsm_first_montly_revenue += data_row.fsm_first_montly_revenue
            total_fsm_first_annual_revenue += data_row.fsm_first_annual_revenue
            total_fsm_recurring_montly_revenue += data_row.fsm_recurring_montly_revenue
            total_fsm_recurring_annual_revenue += data_row.fsm_recurring_annual_revenue
        
        # Calcular métricas
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        cpm = (total_cost / total_impressions * 1000) if total_impressions > 0 else 0
        cpc = (total_cost / total_clicks) if total_clicks > 0 else 0
        conversion_rate = (total_transactions / total_clicks * 100) if total_clicks > 0 else 0
        roas = (total_revenue / total_cost) if total_cost > 0 else 0
        
        # Calcular totais gerais de assinatura
        total_subscriptions = (total_first_montly_subscriptions + total_first_annual_subscriptions + 
                             total_recurring_montly_subscriptions + total_recurring_annual_subscriptions)
        total_subscription_revenue = (total_first_montly_revenue + total_first_annual_revenue + 
                                    total_recurring_montly_revenue + total_recurring_annual_revenue)
        total_fsm_subscriptions = (total_fsm_first_montly_subscriptions + total_fsm_first_annual_subscriptions + 
                                 total_fsm_recurring_montly_subscriptions + total_fsm_recurring_annual_subscriptions)
        total_fsm_subscription_revenue = (total_fsm_first_montly_revenue + total_fsm_first_annual_revenue + 
                                        total_fsm_recurring_montly_revenue + total_fsm_recurring_annual_revenue)
        
        # Criar resumo
        summary = {
            "total_cost": total_cost,
            "total_revenue": total_revenue,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_leads": total_leads,
            "total_transactions": total_transactions,
            "ctr": ctr,  # Click Through Rate
            "cpm": cpm,  # Cost Per Mille (1000 impressions)
            "cpc": cpc,  # Cost Per Click
            "conversion_rate": conversion_rate,
            "roas": roas,  # Return on Ad Spend
            # Métricas de assinatura (último clique)
            "total_subscriptions": total_subscriptions,
            "total_subscription_revenue": total_subscription_revenue,
            "total_first_montly_subscriptions": total_first_montly_subscriptions,
            "total_first_annual_subscriptions": total_first_annual_subscriptions,
            "total_recurring_montly_subscriptions": total_recurring_montly_subscriptions,
            "total_recurring_annual_subscriptions": total_recurring_annual_subscriptions,
            "total_first_montly_revenue": total_first_montly_revenue,
            "total_first_annual_revenue": total_first_annual_revenue,
            "total_recurring_montly_revenue": total_recurring_montly_revenue,
            "total_recurring_annual_revenue": total_recurring_annual_revenue,
            # Métricas de assinatura (primeiro clique - FSM)
            "total_fsm_subscriptions": total_fsm_subscriptions,
            "total_fsm_subscription_revenue": total_fsm_subscription_revenue,
            "total_fsm_first_montly_subscriptions": total_fsm_first_montly_subscriptions,
            "total_fsm_first_annual_subscriptions": total_fsm_first_annual_subscriptions,
            "total_fsm_recurring_montly_subscriptions": total_fsm_recurring_montly_subscriptions,
            "total_fsm_recurring_annual_subscriptions": total_fsm_recurring_annual_subscriptions,
            "total_fsm_first_montly_revenue": total_fsm_first_montly_revenue,
            "total_fsm_first_annual_revenue": total_fsm_first_annual_revenue,
            "total_fsm_recurring_montly_revenue": total_fsm_recurring_montly_revenue,
            "total_fsm_recurring_annual_revenue": total_fsm_recurring_annual_revenue,
            "periodo": f"{start_date_str} a {end_date_str}",
            "tablename": tablename,
            "user_access": "all" if user_tablename == 'all' else "limited"
        }
        
        # Preparar resposta
        response_data = {
            'data': [row.dict() for row in data],
            'total_rows': len(data),
            'summary': summary,
            'cached_at': datetime.now().isoformat()
        }
        
        # Salvar último request
        last_request_manager.save_last_request(
            'ads-campaigns-results',
            {
                'start_date': request.start_date,
                'end_date': request.end_date,
                'table_name': request.table_name
            },
            token.email
        )
        
        # Armazenar no cache
        ads_campaigns_results_cache.set(response_data, **cache_params)
        
        return AdsCampaignsResultsResponse(
            data=data,
            total_rows=len(data),
            summary=summary,
            cache_info={
                'source': 'database',
                'cached_at': response_data['cached_at'],
                'ttl_hours': 168  # 7 dias
            }
        )
        
    except Exception as e:
        print(f"Erro ao buscar dados de campanhas publicitárias: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.post("/ads-creatives-results", response_model=AdsCreativesResultsResponse)
async def get_ads_creatives_results(
    request: AdsCreativesResultsRequest,
    token: TokenData = Depends(verify_token)
):
    
    
    # Se last_cache for True, buscar o último request salvo específico por table_name
    if request.last_cache:
        if not request.table_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="table_name é obrigatório quando last_cache é true"
            )
        
        last_request = last_request_manager.get_last_request('ads-creatives-results', request.table_name)
        if last_request:
            # Executar o último request salvo (se o usuário tem acesso à tabela, pode ver requests de qualquer usuário)
            return await execute_last_request('ads-creatives-results', last_request['request_data'], token)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhum último request encontrado para a tabela '{request.table_name}'"
            )
    
    # Validação para request normal (quando last_cache é false)
    if not request.last_cache:
        if not request.start_date or not request.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date e end_date são obrigatórios quando last_cache é false"
            )
    
    # Parâmetros para o cache
    cache_params = {
        'email': token.email,
        'start_date': request.start_date,
        'end_date': request.end_date,
        'table_name': request.table_name
    }
    
    # Tentar buscar do cache primeiro (apenas se force_refresh for False)
    if not request.force_refresh:
        cached_result = ads_campaigns_results_cache.get(**cache_params)
        if cached_result:
            print(f"Cache hit para ads-creatives-results: {cache_params}")
            return AdsCreativesResultsResponse(**cached_result)
    
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
        
        # Construir query baseada na SQL fornecida
        start_date_str = request.start_date
        end_date_str = request.end_date
        
        query = f"""
        SELECT
            platform,
            campaign_name,
            adset_id,
            adset_name,
            ad_id,
            ad_name,
            date,
            sum(cost) cost,
            sum(impressions) impressions,
            sum(clicks) clicks,
            sum(leads) Leads,
            sum(transactions) transactions,
            sum(revenue) revenue,
            sum(first_transaction) transactions_first,
            sum(first_revenue) revenue_first,
            sum(fsm_transactions) transactions_origin_stack,
            sum(fsm_revenue) revenue_origin_stack,
            sum(fsm_first_transaction) transactions_first_origin_stack,
            sum(fsm_first_revenue) revenue_first_origin_stack
        FROM `{project_name}.dbt_join.{tablename}_ads_creatives_results`
        WHERE date BETWEEN '{start_date_str}' AND '{end_date_str}'
        GROUP BY ALL
        ORDER BY cost DESC
        """
        
        print(f"Executando query ads-creatives-results: {query}")
        
        # Executar query
        result = client.query(query)
        rows = list(result.result())
        
        # Converter para formato de resposta
        data = []
        total_cost = 0
        total_revenue = 0
        total_impressions = 0
        total_clicks = 0
        total_leads = 0
        total_transactions = 0
        
        for row in rows:
            data_row = AdsCreativesResultsRow(
                platform=row.platform or "",
                campaign_name=row.campaign_name or "",
                adset_id=row.adset_id or 0,
                adset_name=row.adset_name or "",
                ad_id=row.ad_id or 0,
                ad_name=row.ad_name or "",
                date=str(row.date) if row.date else "",
                cost=float(row.cost) if row.cost is not None else 0.0,
                impressions=int(row.impressions) if row.impressions is not None else 0,
                clicks=int(row.clicks) if row.clicks is not None else 0,
                leads=int(row.Leads) if row.Leads is not None else 0,
                transactions=int(row.transactions) if row.transactions is not None else 0,
                revenue=float(row.revenue) if row.revenue is not None else 0.0,
                transactions_first=int(row.transactions_first) if row.transactions_first is not None else 0,
                revenue_first=float(row.revenue_first) if row.revenue_first is not None else 0.0,
                transactions_origin_stack=int(row.transactions_origin_stack) if row.transactions_origin_stack is not None else 0,
                revenue_origin_stack=float(row.revenue_origin_stack) if row.revenue_origin_stack is not None else 0.0,
                transactions_first_origin_stack=int(row.transactions_first_origin_stack) if row.transactions_first_origin_stack is not None else 0,
                revenue_first_origin_stack=float(row.revenue_first_origin_stack) if row.revenue_first_origin_stack is not None else 0.0
            )
            data.append(data_row)
            
            # Acumular totais
            total_cost += data_row.cost
            total_revenue += data_row.revenue
            total_impressions += data_row.impressions
            total_clicks += data_row.clicks
            total_leads += data_row.leads
            total_transactions += data_row.transactions
        
        # Calcular métricas de resumo
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        cpc = (total_cost / total_clicks) if total_clicks > 0 else 0
        cpm = (total_cost / total_impressions * 1000) if total_impressions > 0 else 0
        conversion_rate = (total_transactions / total_clicks * 100) if total_clicks > 0 else 0
        roas = (total_revenue / total_cost) if total_cost > 0 else 0
        
        summary = {
            "total_cost": total_cost,
            "total_revenue": total_revenue,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_leads": total_leads,
            "total_transactions": total_transactions,
            "ctr": round(ctr, 2),  # Click Through Rate
            "cpc": round(cpc, 2),  # Cost Per Click
            "cpm": round(cpm, 2),  # Cost Per Mille
            "conversion_rate": round(conversion_rate, 2),
            "roas": round(roas, 2),  # Return on Ad Spend
            "periodo": f"{start_date_str} a {end_date_str}",
            "tablename": tablename,
            "user_access": "all" if user_tablename == 'all' else "limited"
        }
        
        # Preparar resposta
        response_data = {
            'data': [row.dict() for row in data],
            'total_rows': len(data),
            'summary': summary,
            'cached_at': datetime.now().isoformat()
        }
        
        # Salvar último request
        last_request_manager.save_last_request(
            'ads-creatives-results',
            {
                'start_date': request.start_date,
                'end_date': request.end_date,
                'table_name': request.table_name
            },
            token.email
        )
        
        # Armazenar no cache (usando o mesmo cache do ads-campaigns-results)
        ads_campaigns_results_cache.set(response_data, **cache_params)
        
        return AdsCreativesResultsResponse(
            data=data,
            total_rows=len(data),
            summary=summary,
            cache_info={
                'source': 'database',
                'cached_at': response_data['cached_at'],
                'ttl_hours': 168  # 7 dias
            }
        )
        
    except Exception as e:
        print(f"Erro ao buscar dados de criativos publicitários: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.post("/realtime", response_model=RealtimeResponse)
async def get_realtime_purchases(
    request: RealtimeRequest,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar dados de compras de itens em tempo real com cache de 15 minutos"""
    
    # Usar limite se fornecido, senão buscar todos os dados
    limit = request.limit
    
    # Parâmetros para o cache
    cache_params = {
        'email': token.email,
        'table_name': request.table_name,
        'limit': limit
    }
    
    # Tentar buscar do cache primeiro
    cached_data = realtime_cache.get(**cache_params)
    if cached_data:
        return RealtimeResponse(
            data=cached_data['data'],
            total_rows=cached_data['total_rows'],
            summary=cached_data['summary'],
            cache_info={
                'source': 'cache',
                'cached_at': cached_data.get('cached_at'),
                'ttl_hours': 0.25
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

        # Determinar projeto
        project_name = get_project_name(tablename)
        
        # Construir query realtime
        limit_clause = f"LIMIT {limit}" if limit else ""
        query = f"""
        SELECT
            event_timestamp,
            concat(ga_session_id, user_pseudo_id) session_id,
            transaction_id,
            item_category,
            item_name,
            quantity,
            item_revenue,
            source,
            medium,
            campaign,
            content,
            term,
            page_location,
            traffic_category
        FROM
            `{project_name}.dbt_join.{tablename}_purchases_items_sessions_realtime`
        ORDER BY event_timestamp DESC
        {limit_clause}
        """
        
        print(f"Executando query realtime: {query}")
        
        # Executar query
        result = client.query(query)
        rows = list(result.result())
        
        # Converter para formato de resposta
        data = []
        total_revenue = 0
        total_quantity = 0
        unique_transactions = set()
        unique_sessions = set()
        
        for row in rows:
            # Converter timestamp se necessário
            event_timestamp_str = str(row.event_timestamp) if row.event_timestamp else ""
            if hasattr(row.event_timestamp, 'isoformat'):
                event_timestamp_str = row.event_timestamp.isoformat()
            
            data_row = RealtimeRow(
                event_timestamp=event_timestamp_str,
                session_id=str(row.session_id) if row.session_id else "",
                transaction_id=str(row.transaction_id) if row.transaction_id else "",
                item_category=str(row.item_category) if row.item_category else "",
                item_name=str(row.item_name) if row.item_name else "",
                quantity=int(row.quantity) if row.quantity else 0,
                item_revenue=float(row.item_revenue) if row.item_revenue else 0.0,
                source=str(row.source) if row.source else "",
                medium=str(row.medium) if row.medium else "",
                campaign=str(row.campaign) if row.campaign else "",
                content=str(row.content) if row.content else "",
                term=str(row.term) if row.term else "",
                page_location=str(row.page_location) if row.page_location else "",
                traffic_category=str(row.traffic_category) if row.traffic_category else ""
            )
            data.append(data_row)
            
            # Calcular totais
            total_revenue += data_row.item_revenue
            total_quantity += data_row.quantity
            if data_row.transaction_id:
                unique_transactions.add(data_row.transaction_id)
            if data_row.session_id:
                unique_sessions.add(data_row.session_id)
        
        # Calcular métricas
        avg_item_value = total_revenue / len(data) if len(data) > 0 else 0
        avg_quantity_per_item = total_quantity / len(data) if len(data) > 0 else 0
        
        # Criar resumo
        summary = {
            "total_items": len(data),
            "total_revenue": total_revenue,
            "total_quantity": total_quantity,
            "unique_transactions": len(unique_transactions),
            "unique_sessions": len(unique_sessions),
            "avg_item_value": avg_item_value,
            "avg_quantity_per_item": avg_quantity_per_item,
            "tablename": tablename,
            "user_access": "all" if user_tablename == 'all' else "limited",
            "limit_applied": limit,
            "data_freshness": "realtime"
        }
        
        # Preparar resposta
        response_data = {
            'data': [row.dict() for row in data],
            'total_rows': len(data),
            'summary': summary,
            'cached_at': datetime.now().isoformat()
        }
        
        # Salvar último request
        last_request_manager.save_last_request(
            'realtime',
            {
                'table_name': request.table_name,
                'limit': limit
            },
            token.email
        )
        
        # Armazenar no cache
        realtime_cache.set(response_data, **cache_params)
        
        return RealtimeResponse(
            data=data,
            total_rows=len(data),
            summary=summary,
            cache_info={
                'source': 'database',
                'cached_at': response_data['cached_at'],
                'ttl_hours': 0.25
            }
        )
        
    except Exception as e:
        print(f"Erro ao buscar dados realtime: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )


async def execute_last_request(endpoint: str, request_data: Dict[str, Any], token: TokenData):
    """Função auxiliar para executar a consulta baseada no último request"""
    
    if endpoint == "basic-data":
        from pydantic import BaseModel
        class TempRequest(BaseModel):
            start_date: str
            end_date: str
            attribution_model: Optional[str] = "Último Clique Não Direto"
            filters: Optional[Dict[str, Any]] = None
            table_name: Optional[str] = None
        
        temp_request = TempRequest(**request_data)
        return await get_basic_data(temp_request, token)
    
    elif endpoint == "daily-metrics":
        from pydantic import BaseModel
        class TempRequest(BaseModel):
            start_date: str
            end_date: str
            table_name: Optional[str] = None
        
        temp_request = TempRequest(**request_data)
        return await get_daily_metrics(temp_request, token)
    
    elif endpoint == "orders":
        from pydantic import BaseModel
        class TempRequest(BaseModel):
            start_date: str
            end_date: str
            table_name: Optional[str] = None
            limit: Optional[int] = 1000
            offset: Optional[int] = 0
            traffic_category: Optional[str] = None
            fs_traffic_category: Optional[str] = None
            fsm_traffic_category: Optional[str] = None
        
        temp_request = TempRequest(**request_data)
        return await get_orders(temp_request, token)
    
    elif endpoint == "goals":
        from pydantic import BaseModel
        class TempRequest(BaseModel):
            table_name: str
        
        temp_request = TempRequest(**request_data)
        return await get_user_goals(temp_request, token)
    
    elif endpoint == "detailed-data":
        from pydantic import BaseModel
        class TempRequest(BaseModel):
            start_date: str
            end_date: str
            attribution_model: Optional[str] = "purchase"
            table_name: Optional[str] = None
            limit: Optional[int] = 1000
            offset: Optional[int] = 0
            order_by: Optional[str] = "Pedidos"
        
        temp_request = TempRequest(**request_data)
        return await get_detailed_data(temp_request, token)
    
    elif endpoint == "product-trend":
        from pydantic import BaseModel
        class TempRequest(BaseModel):
            table_name: str
            limit: Optional[int] = 100
            offset: Optional[int] = 0
            order_by: Optional[str] = "purchases_week_4"
        
        temp_request = TempRequest(**request_data)
        return await get_product_trend(temp_request, token)
    
    elif endpoint == "ads-campaigns-results":
        from pydantic import BaseModel
        class TempRequest(BaseModel):
            start_date: Optional[str] = None
            end_date: Optional[str] = None
            table_name: Optional[str] = None
            last_cache: Optional[bool] = False
            force_refresh: Optional[bool] = False
        
        temp_request = TempRequest(**request_data)
        # Garantir que last_cache seja False para evitar loop infinito
        temp_request.last_cache = False
        return await get_ads_campaigns_results(temp_request, token)
    
    elif endpoint == "ads-creatives-results":
        from pydantic import BaseModel
        class TempRequest(BaseModel):
            start_date: Optional[str] = None
            end_date: Optional[str] = None
            table_name: Optional[str] = None
            last_cache: Optional[bool] = False
            force_refresh: Optional[bool] = False
        
        temp_request = TempRequest(**request_data)
        # Garantir que last_cache seja False para evitar loop infinito
        temp_request.last_cache = False
        return await get_ads_creatives_results(temp_request, token)
    
    elif endpoint == "realtime":
        from pydantic import BaseModel
        class TempRequest(BaseModel):
            table_name: Optional[str] = None
            limit: Optional[int] = None
        
        temp_request = TempRequest(**request_data)
        return await get_realtime_purchases(temp_request, token)
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Endpoint '{endpoint}' não suportado para execução automática"
        )

@metrics_router.get("/last-request/stats")
async def get_last_request_stats(token: TokenData = Depends(verify_token)):
    """Endpoint para ver estatísticas do storage de últimos requests"""
    try:
        stats = last_request_manager.get_storage_stats()
        return {
            "message": "Estatísticas do storage de últimos requests",
            "stats": stats
        }
    except Exception as e:
        print(f"Erro ao buscar estatísticas do last-request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.get("/last-request/{endpoint}/all")
async def get_all_last_requests(
    endpoint: str,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar todos os últimos requests de um endpoint para todos os clientes"""
    
    try:
        all_requests = last_request_manager.get_all_last_requests(endpoint)
        
        if not all_requests:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhum request encontrado para o endpoint '{endpoint}'"
            )
        
        # Filtrar apenas requests do usuário atual
        user_requests = {}
        for table_name, request_data in all_requests.items():
            if request_data['user_email'] == token.email:
                user_requests[table_name] = request_data
        
        if not user_requests:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhum request encontrado para o endpoint '{endpoint}' do seu usuário"
            )
        
        return {
            "endpoint": endpoint,
            "requests": user_requests
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao buscar todos os últimos requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.get("/last-request/{endpoint}")
async def get_last_request(
    endpoint: str,
    table_name: str,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar e executar o último request de um endpoint específico para um cliente específico"""
    
    try:
        last_request = last_request_manager.get_last_request(endpoint, table_name)
        
        if not last_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhum request encontrado para o endpoint '{endpoint}' e cliente '{table_name}'"
            )
        
        # Verificar se o usuário tem permissão para ver este request
        if last_request['user_email'] != token.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode ver seus próprios últimos requests"
            )
        
        # Executar a consulta automaticamente
        print(f"🔄 Executando último request para {endpoint} - Cliente: {table_name}")
        result = await execute_last_request(endpoint, last_request['request_data'], token)
        
        # Adicionar informações do último request ao resultado
        if hasattr(result, 'dict'):
            result_dict = result.dict()
        else:
            result_dict = result
        
        result_dict['last_request_info'] = {
            "endpoint": endpoint,
            "table_name": table_name,
            "request_data": last_request['request_data'],
            "user_email": last_request['user_email'],
            "timestamp": last_request['timestamp'],
            "executed_at": datetime.now().isoformat()
        }
        
        return result_dict
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao executar último request: {e}")
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
        
        # Fazer flush de todos os caches
        basic_stats = basic_data_cache.flush()
        daily_metrics_stats = daily_metrics_cache.flush()
        orders_stats = orders_cache.flush()
        detailed_data_stats = detailed_data_cache.flush()
        product_trend_stats = product_trend_cache.flush()
        ads_campaigns_results_stats = ads_campaigns_results_cache.flush()
        realtime_stats = realtime_cache.flush()
        
        return {
            "message": "Todos os caches limpos com sucesso",
            "stats": {
                "basic_data_cache": basic_stats,
                "daily_metrics_cache": daily_metrics_stats,
                "orders_cache": orders_stats,
                "detailed_data_cache": detailed_data_stats,
                "product_trend_cache": product_trend_stats,
                "ads_campaigns_results_cache": ads_campaigns_results_stats,
                "realtime_cache": realtime_stats
            }
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
        
        # Fazer flush apenas das entradas expiradas de todos os caches
        basic_stats = basic_data_cache.flush_expired()
        daily_metrics_stats = daily_metrics_cache.flush_expired()
        orders_stats = orders_cache.flush_expired()
        detailed_data_stats = detailed_data_cache.flush_expired()
        product_trend_stats = product_trend_cache.flush_expired()
        ads_campaigns_results_stats = ads_campaigns_results_cache.flush_expired()
        realtime_stats = realtime_cache.flush_expired()
        
        return {
            "message": "Entradas expiradas removidas com sucesso de todos os caches",
            "stats": {
                "basic_data_cache": basic_stats,
                "daily_metrics_cache": daily_metrics_stats,
                "orders_cache": orders_stats,
                "detailed_data_cache": detailed_data_stats,
                "product_trend_cache": product_trend_stats,
                "ads_campaigns_results_cache": ads_campaigns_results_stats,
                "realtime_cache": realtime_stats
            }
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
        
        # Obter estatísticas de todos os caches
        basic_stats = basic_data_cache.get_stats()
        daily_metrics_stats = daily_metrics_cache.get_stats()
        orders_stats = orders_cache.get_stats()
        detailed_data_stats = detailed_data_cache.get_stats()
        product_trend_stats = product_trend_cache.get_stats()
        ads_campaigns_results_stats = ads_campaigns_results_cache.get_stats()
        realtime_stats = realtime_cache.get_stats()
        
        return {
            "message": "Estatísticas de todos os caches",
            "stats": {
                "basic_data_cache": basic_stats,
                "daily_metrics_cache": daily_metrics_stats,
                "orders_cache": orders_stats,
                "detailed_data_cache": detailed_data_stats,
                "product_trend_cache": product_trend_stats,
                "ads_campaigns_results_cache": ads_campaigns_results_stats,
                "realtime_cache": realtime_stats
            }
        }
        
    except Exception as e:
        print(f"Erro ao obter estatísticas do cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@metrics_router.post("/leads_orders", response_model=LeadsOrdersResponse)
async def get_leads_orders(
    request: LeadsOrdersRequest,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar dados de leads e orders com cache de 1 hora"""
    
    # Parâmetros para o cache
    cache_params = {
        'email': token.email,
        'start_date': request.start_date,
        'end_date': request.end_date,
        'table_name': request.table_name
    }
    
    # Tentar buscar do cache primeiro
    cached_data = basic_data_cache.get(**cache_params)
    if cached_data:
        return LeadsOrdersResponse(
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
        SELECT tablename, admin, access_control
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
        is_admin = user_data[0].admin
        
        # Determinar qual tabela usar
        if is_admin and request.table_name:
            tablename = request.table_name
        elif user_tablename == 'all':
            tablename = request.table_name
        else:
            tablename = user_tablename
        
        # Construir nome da tabela
        table_name = f"dbt_join.{tablename}_leads_orders_"
        
        # Query para buscar dados de leads_orders
        query = f"""
        SELECT
            subscribe_timestamp,
            name,
            phone,
            email,
            fsm_source,
            fsm_medium,
            fsm_campaign,
            transaction_id,
            purchase_timestamp,
            value,
            source,
            medium,
            campaign,
            days_between_subscribe_and_purchase,
            minutes_between_subscribe_and_purchase
        FROM `{table_name}`
        WHERE DATE(subscribe_timestamp) BETWEEN @start_date AND @end_date
           OR DATE(purchase_timestamp) BETWEEN @start_date AND @end_date
        ORDER BY subscribe_timestamp DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "STRING", request.start_date),
                bigquery.ScalarQueryParameter("end_date", "STRING", request.end_date),
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        # Converter resultados para o modelo
        data = []
        total_leads = 0
        total_orders = 0
        total_revenue = 0.0
        
        for row in results:
            leads_row = LeadsOrdersRow(
                subscribe_timestamp=str(row.subscribe_timestamp) if row.subscribe_timestamp else None,
                name=str(row.name) if row.name else None,
                phone=str(row.phone) if row.phone else None,
                email=str(row.email) if row.email else None,
                fsm_source=str(row.fsm_source) if row.fsm_source else None,
                fsm_medium=str(row.fsm_medium) if row.fsm_medium else None,
                fsm_campaign=str(row.fsm_campaign) if row.fsm_campaign else None,
                transaction_id=str(row.transaction_id) if row.transaction_id else None,
                purchase_timestamp=str(row.purchase_timestamp) if row.purchase_timestamp else None,
                value=float(row.value) if row.value is not None else None,
                source=str(row.source) if row.source else None,
                medium=str(row.medium) if row.medium else None,
                campaign=str(row.campaign) if row.campaign else None,
                days_between_subscribe_and_purchase=int(row.days_between_subscribe_and_purchase) if row.days_between_subscribe_and_purchase is not None else None,
                minutes_between_subscribe_and_purchase=int(row.minutes_between_subscribe_and_purchase) if row.minutes_between_subscribe_and_purchase is not None else None
            )
            data.append(leads_row)
            
            # Calcular métricas
            if row.subscribe_timestamp:
                total_leads += 1
            if row.transaction_id:
                total_orders += 1
            if row.value is not None:
                total_revenue += float(row.value)
        
        # Criar resumo
        summary = {
            "total_leads": total_leads,
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "conversion_rate": round((total_orders / total_leads * 100) if total_leads > 0 else 0, 2),
            "periodo": f"{request.start_date} a {request.end_date}",
            "tablename": tablename,
            "user_access": "all" if user_tablename == 'all' else "limited"
        }
        
        # Preparar resposta
        response_data = {
            'data': [row.dict() for row in data],
            'total_rows': len(data),
            'summary': summary,
            'cached_at': datetime.now().isoformat()
        }
        
        # Salvar último request
        last_request_manager.save_last_request(
            'leads_orders',
            {
                'start_date': request.start_date,
                'end_date': request.end_date,
                'table_name': request.table_name
            },
            token.email
        )
        
        # Armazenar no cache
        basic_data_cache.set(response_data, **cache_params)
        
        return LeadsOrdersResponse(
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
        print(f"Erro ao buscar dados de leads_orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )
