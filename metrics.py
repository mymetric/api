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
from cache_manager import basic_data_cache, daily_metrics_cache, orders_cache, detailed_data_cache, last_request_manager

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
    limit: Optional[int] = 1000  # Limitar resultados
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
    data: List[DetailedDataRow]
    total_rows: int
    summary: Dict[str, Any]
    cache_info: Optional[Dict[str, Any]] = None
    pagination: Optional[Dict[str, Any]] = None

# Modelos para product trend
class ProductTrendRequest(BaseModel):
    table_name: str
    limit: Optional[int] = 100

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

class ProductTrendResponse(BaseModel):
    data: List[ProductTrendRow]
    total_rows: int
    summary: Dict[str, Any]

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
                    SUM(CASE WHEN event_name = 'paid_media' then value else 0 end) AS Investimento,
                    SUM(CASE WHEN event_name = 'paid_media' then clicks else 0 end) AS Cliques,
                    COUNTIF(event_name = 'session') AS Sessoes,
                    COUNTIF(event_name = 'add_to_cart') AS Adicoes_ao_Carrinho,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' then transaction_id end) AS Pedidos,
                    SUM(CASE WHEN event_name = '{attribution_model}' then value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) end) AS Receita,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') THEN transaction_id END) AS Pedidos_Pagos,
                    SUM(CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') THEN value ELSE 0 END) AS Receita_Paga,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') and transaction_no = 1 THEN transaction_id END) AS Novos_Clientes,
                    SUM(CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') and transaction_no = 1 THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Novos_Clientes"""
        else:
            base_query = f"""
                SELECT
                    event_date AS Data,
                    traffic_category AS Cluster,
                    SUM(CASE WHEN event_name = 'paid_media' then value else 0 end) AS Investimento,
                    SUM(CASE WHEN event_name = 'paid_media' then clicks else 0 end) AS Cliques,
                    COUNTIF(event_name = 'session') AS Sessoes,
                    COUNTIF(event_name = 'add_to_cart') AS Adicoes_ao_Carrinho,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' then transaction_id end) AS Pedidos,
                    SUM(CASE WHEN event_name = '{attribution_model}' then value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) end) AS Receita,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') THEN transaction_id END) AS Pedidos_Pagos,
                    SUM(CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Paga,
                    COUNT(DISTINCT CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') and transaction_no = 1 THEN transaction_id END) AS Novos_Clientes,
                    SUM(CASE WHEN event_name = '{attribution_model}' and status in ('paid', 'authorized') and transaction_no = 1 THEN value - coalesce(total_discounts, 0) + coalesce(shipping_value, 0) ELSE 0 END) AS Receita_Novos_Clientes"""

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
    limit = min(request.limit or 1000, 5000)  # Máximo 5000 registros
    offset = max(request.offset or 0, 0)      # Offset não pode ser negativo
    
    if request.limit and request.limit > 5000:
        print(f"⚠️ Limite muito alto ({request.limit}), usando máximo de 5000")
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
        
        # Query principal com UNION para separar diferentes tipos de eventos
        query = f"""
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
        ORDER BY {order_by} DESC
        LIMIT {limit} OFFSET {offset}
        """
        
        print(f"Executando query de dados detalhados com paginação: limit={limit}, offset={offset}, order_by={order_by}")
        print(f"Query length: {len(query)}")
        print(f"Query contains 'WITH session_data': {'WITH session_data' in query}")
        print(f"Query contains 'UNION ALL': {'UNION ALL' in query}")
        
        # Executar query
        result = client.query(query)
        rows = list(result.result())
        
        # Processar resultados
        data = []
        total_revenue = 0.0
        total_orders = 0
        total_sessions = 0
        total_add_to_cart = 0
        
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
            
            total_revenue += float(row.Receita) if row.Receita else 0.0
            total_orders += int(row.Pedidos) if row.Pedidos else 0
            total_sessions += int(row.Sessoes) if row.Sessoes else 0
            total_add_to_cart += int(row.Adicoes_ao_Carrinho) if row.Adicoes_ao_Carrinho else 0
        
        # Calcular resumo
        summary = {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_sessions": total_sessions,
            "total_add_to_cart": total_add_to_cart,
            "conversion_rate": (total_orders / total_sessions * 100) if total_sessions > 0 else 0,
            "add_to_cart_rate": (total_add_to_cart / total_sessions * 100) if total_sessions > 0 else 0,
            "table_name": tablename,
            "project_name": project_name,
            "attribution_model": request.attribution_model
        }
        
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
    """Endpoint para buscar dados de tendência de produtos"""
    
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
        
        # Query para buscar dados de tendência de produtos
        query = f"""
        SELECT
            item_id,
            item_name,
            purchases_week_1,
            purchases_week_2,
            purchases_week_3,
            purchases_week_4,
            percent_change_w1_w2,
            percent_change_w2_w3,
            percent_change_w3_w4,
            trend_status,
            trend_consistency
        FROM `{project_name}.dbt_aggregated.{tablename}_product_trend`
        ORDER BY purchases_week_4 DESC
        LIMIT {request.limit}
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
            data_row = ProductTrendRow(
                item_id=str(row.item_id) if row.item_id else "",
                item_name=str(row.item_name) if row.item_name else "",
                purchases_week_1=int(row.purchases_week_1) if row.purchases_week_1 is not None else 0,
                purchases_week_2=int(row.purchases_week_2) if row.purchases_week_2 is not None else 0,
                purchases_week_3=int(row.purchases_week_3) if row.purchases_week_3 is not None else 0,
                purchases_week_4=int(row.purchases_week_4) if row.purchases_week_4 is not None else 0,
                percent_change_w1_w2=float(row.percent_change_w1_w2) if row.percent_change_w1_w2 is not None else 0.0,
                percent_change_w2_w3=float(row.percent_change_w2_w3) if row.percent_change_w2_w3 is not None else 0.0,
                percent_change_w3_w4=float(row.percent_change_w3_w4) if row.percent_change_w3_w4 is not None else 0.0,
                trend_status=str(row.trend_status) if row.trend_status else "",
                trend_consistency=str(row.trend_consistency) if row.trend_consistency else ""
            )
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
            "limit_applied": request.limit
        }
        
        # Salvar último request
        last_request_manager.save_last_request(
            'product-trend',
            {
                'table_name': request.table_name,
                'limit': request.limit
            },
            token.email
        )
        
        return ProductTrendResponse(
            data=data,
            total_rows=len(data),
            summary=summary
        )
        
    except Exception as e:
        print(f"Erro ao buscar dados de tendência de produtos: {e}")
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
        
        temp_request = TempRequest(**request_data)
        return await get_product_trend(temp_request, token)
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Endpoint '{endpoint}' não suportado para execução automática"
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
        
        return {
            "message": "Todos os caches limpos com sucesso",
            "stats": {
                "basic_data_cache": basic_stats,
                "daily_metrics_cache": daily_metrics_stats,
                "orders_cache": orders_stats,
                "detailed_data_cache": detailed_data_stats
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
        
        return {
            "message": "Entradas expiradas removidas com sucesso de todos os caches",
            "stats": {
                "basic_data_cache": basic_stats,
                "daily_metrics_cache": daily_metrics_stats,
                "orders_cache": orders_stats,
                "detailed_data_cache": detailed_data_stats
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
        
        return {
            "message": "Estatísticas de todos os caches",
            "stats": {
                "basic_data_cache": basic_stats,
                "daily_metrics_cache": daily_metrics_stats,
                "orders_cache": orders_stats,
                "detailed_data_cache": detailed_data_stats
            }
        }
        
    except Exception as e:
        print(f"Erro ao obter estatísticas do cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        ) 