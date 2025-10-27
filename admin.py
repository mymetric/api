"""
Módulo de endpoints para administração
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from google.cloud import bigquery
from datetime import datetime
import json

from utils import verify_token, TokenData, get_bigquery_client

# Router para admin
admin_router = APIRouter(prefix="/admin", tags=["admin"])

# Modelos para categorias de tráfego
class TrafficCategoryRules(BaseModel):
    origem: Optional[str] = None
    midia: Optional[str] = None
    campaign: Optional[str] = None
    page_location: Optional[str] = None
    parametros_url: Optional[str] = None
    cupom: Optional[str] = None

class TrafficCategoryRequest(BaseModel):
    category_name: str
    description: str
    rules: Dict[str, Any]  # Formato: {"type": "regex", "rules": {...}}
    table_name: Optional[str] = None

class TrafficCategoryResponse(BaseModel):
    success: bool
    message: str
    category_name: Optional[str] = None

class DeleteTrafficCategoryRequest(BaseModel):
    category_name: str
    table_name: Optional[str] = None

class TrafficCategoryRow(BaseModel):
    nome: str
    descricao: str
    regras: Dict[str, Any]

class LoadTrafficCategoriesRequest(BaseModel):
    table_name: Optional[str] = None

class TrafficCategoriesResponse(BaseModel):
    data: List[TrafficCategoryRow]
    total_rows: int

class SaveMonthlyGoalRequest(BaseModel):
    table_name: str
    month: str  # Formato: YYYY-MM
    goal_value: float
    goal_type: str  # Ex: "revenue_goal", "orders_goal", "conversion_rate_goal"

class LoadGoalsRequest(BaseModel):
    table_name: str

class LoadGoalsResponse(BaseModel):
    success: bool
    message: str
    goals: Optional[Dict[str, Any]] = None
    username: Optional[str] = None

class DeleteGoalRequest(BaseModel):
    table_name: str
    month: str  # Formato: YYYY-MM
    goal_type: str  # Ex: "revenue_goal", "orders_goal", "conversion_rate_goal"

class DeleteGoalResponse(BaseModel):
    success: bool
    message: str
    deleted_goal: Optional[Dict[str, Any]] = None

class CleanGoalsRequest(BaseModel):
    table_name: str

class CleanGoalsResponse(BaseModel):
    success: bool
    message: str
    cleaned_goals: Optional[Dict[str, Any]] = None

@admin_router.post("/traffic-categories", response_model=TrafficCategoryResponse)
async def save_traffic_category(
    request: TrafficCategoryRequest,
    token: TokenData = Depends(verify_token)
):
    """
    Salva uma nova categoria de tráfego no BigQuery.
    """
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
        
        # Determinar qual tablename usar
        if request.table_name:
            # Usuário especificou uma tabela
            if user_tablename == 'all':
                # Usuário com acesso total pode salvar para qualquer tabela
                tablename = request.table_name
                print(f"🔓 Usuário com acesso total salvando categoria para tabela: {tablename}")
            else:
                # Usuário com acesso limitado só pode salvar para sua própria tabela
                if request.table_name != user_tablename:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode salvar categoria para a tabela '{request.table_name}'"
                    )
                tablename = request.table_name
                print(f"🔒 Usuário com acesso limitado salvando categoria para tabela: {tablename}")
        else:
            # Usuário não especificou tabela, usar a tabela padrão do usuário
            tablename = user_tablename
            print(f"📊 Usando tabela padrão do usuário: {tablename}")

        # Verificar se a categoria já existe usando parâmetros
        check_query = """
            SELECT COUNT(*) as count
            FROM `mymetric-hub-shopify.dbt_config.traffic_categories`
            WHERE tablename = @tablename
            AND category_name = @category_name
        """
        
        check_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("tablename", "STRING", tablename),
                bigquery.ScalarQueryParameter("category_name", "STRING", request.category_name),
            ]
        )
        
        check_result = client.query(check_query, job_config=check_config).result()
        count = next(check_result).count

        if count > 0:
            return TrafficCategoryResponse(
                success=False,
                message="Esta categoria já existe!",
                category_name=request.category_name
            )

        # Converter regras para JSON
        rules_json = json.dumps(request.rules)

        # Inserir nova categoria usando parâmetros
        insert_query = """
            INSERT INTO `mymetric-hub-shopify.dbt_config.traffic_categories`
            (tablename, category_name, description, rules, created_at)
            VALUES
            (@tablename, @category_name, @description, @rules, CURRENT_TIMESTAMP())
        """
        
        insert_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("tablename", "STRING", tablename),
                bigquery.ScalarQueryParameter("category_name", "STRING", request.category_name),
                bigquery.ScalarQueryParameter("description", "STRING", request.description),
                bigquery.ScalarQueryParameter("rules", "STRING", rules_json),
            ]
        )

        client.query(insert_query, job_config=insert_config).result()
        print(f"Categoria {request.category_name} salva com sucesso")
        
        return TrafficCategoryResponse(
            success=True,
            message=f"Categoria '{request.category_name}' salva com sucesso!",
            category_name=request.category_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao salvar categoria: {str(e)}")
        print(f"Tipo do erro: {type(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        
        return TrafficCategoryResponse(
            success=False,
            message=f"Erro interno do servidor: {str(e)}",
            category_name=request.category_name
        )

@admin_router.delete("/traffic-categories", response_model=TrafficCategoryResponse)
async def delete_traffic_category(
    request: DeleteTrafficCategoryRequest,
    token: TokenData = Depends(verify_token)
):
    """
    Deleta uma categoria de tráfego do BigQuery.
    """
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
        
        # Determinar qual tablename usar
        if request.table_name:
            # Usuário especificou uma tabela
            if user_tablename == 'all':
                # Usuário com acesso total pode deletar categorias de qualquer tabela
                tablename = request.table_name
                print(f"🔓 Usuário com acesso total deletando categoria da tabela: {tablename}")
            else:
                # Usuário com acesso limitado só pode deletar categorias de sua própria tabela
                if request.table_name != user_tablename:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode deletar categoria da tabela '{request.table_name}'"
                    )
                tablename = request.table_name
                print(f"🔒 Usuário com acesso limitado deletando categoria da tabela: {tablename}")
        else:
            # Usuário não especificou tabela, usar a tabela padrão do usuário
            tablename = user_tablename
            print(f"📊 Usando tabela padrão do usuário: {tablename}")

        # Verificar se a categoria existe
        check_query = """
            SELECT COUNT(*) as count
            FROM `mymetric-hub-shopify.dbt_config.traffic_categories`
            WHERE tablename = @tablename
            AND category_name = @category_name
        """
        
        check_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("tablename", "STRING", tablename),
                bigquery.ScalarQueryParameter("category_name", "STRING", request.category_name),
            ]
        )
        
        check_result = client.query(check_query, job_config=check_config).result()
        count = next(check_result).count

        if count == 0:
            return TrafficCategoryResponse(
                success=False,
                message="Categoria não encontrada!",
                category_name=request.category_name
            )

        # Deletar a categoria
        delete_query = """
            DELETE FROM `mymetric-hub-shopify.dbt_config.traffic_categories`
            WHERE tablename = @tablename
            AND category_name = @category_name
        """
        
        delete_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("tablename", "STRING", tablename),
                bigquery.ScalarQueryParameter("category_name", "STRING", request.category_name),
            ]
        )

        client.query(delete_query, job_config=delete_config).result()
        print(f"Categoria {request.category_name} deletada com sucesso")
        
        return TrafficCategoryResponse(
            success=True,
            message=f"Categoria '{request.category_name}' deletada com sucesso!",
            category_name=request.category_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao deletar categoria: {str(e)}")
        print(f"Tipo do erro: {type(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        
        return TrafficCategoryResponse(
            success=False,
            message=f"Erro interno do servidor: {str(e)}",
            category_name=request.category_name
        )

@admin_router.post("/load-traffic-categories", response_model=TrafficCategoriesResponse)
async def load_traffic_categories(
    request: LoadTrafficCategoriesRequest,
    token: TokenData = Depends(verify_token)
):
    """
    Carrega as categorias de tráfego do BigQuery.
    """
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
        
        # Determinar qual tablename usar
        if request.table_name:
            # Usuário especificou uma tabela
            if user_tablename == 'all':
                # Usuário com acesso total pode carregar categorias de qualquer tabela
                tablename = request.table_name
                print(f"🔓 Usuário com acesso total carregando categorias da tabela: {tablename}")
            else:
                # Usuário com acesso limitado só pode carregar categorias de sua própria tabela
                if request.table_name != user_tablename:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode carregar categorias da tabela '{request.table_name}'"
                    )
                tablename = request.table_name
                print(f"🔒 Usuário com acesso limitado carregando categorias da tabela: {tablename}")
        else:
            # Usuário não especificou tabela, usar a tabela padrão do usuário
            tablename = user_tablename
            print(f"📊 Usando tabela padrão do usuário: {tablename}")

        # Usar parâmetros de consulta para evitar problemas com caracteres especiais
        query = """
            SELECT 
                category_name as nome,
                description as descricao,
                rules as regras
            FROM `mymetric-hub-shopify.dbt_config.traffic_categories`
            WHERE tablename = @tablename
            ORDER BY category_name
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("tablename", "STRING", tablename),
            ]
        )
        
        print(f"Executando query com tablename: {tablename}")
        query_job = client.query(query, job_config=job_config)
        rows = query_job.result()
        
        data = []
        for row in rows:
            # Converter regras de JSON para dicionário
            regras = {}
            if row.regras:
                try:
                    regras = json.loads(row.regras) if isinstance(row.regras, str) else row.regras
                except:
                    regras = {}
            
            data_row = TrafficCategoryRow(
                nome=str(row.nome) if row.nome else "",
                descricao=str(row.descricao) if row.descricao else "",
                regras=regras
            )
            data.append(data_row)
        
        print(f"Carregadas {len(data)} categorias para tablename: {tablename}")
        
        return TrafficCategoriesResponse(
            data=data,
            total_rows=len(data)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao carregar categorias: {str(e)}")
        print(f"Tipo do erro: {type(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@admin_router.post("/save-monthly-goal")
async def save_monthly_goal(
    request: SaveMonthlyGoalRequest,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para salvar meta do mês"""
    
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
            # Usuário com acesso total pode salvar metas para qualquer tabela
            tablename = request.table_name
            print(f"🔓 Usuário com acesso total salvando meta para tabela: {tablename}")
        else:
            # Usuário com acesso limitado só pode salvar metas para sua própria tabela
            if request.table_name != user_tablename:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode salvar metas para a tabela '{request.table_name}'"
                )
            tablename = request.table_name
            print(f"🔒 Usuário com acesso limitado salvando meta para tabela: {tablename}")

        # Buscar metas existentes
        goals_query = f"""
        SELECT goals
        FROM `mymetric-hub-shopify.dbt_config.user_goals`
        WHERE username = '{tablename}'
        LIMIT 1
        """
        
        goals_result = client.query(goals_query)
        goals_data = list(goals_result.result())
        
        # Inicializar metas se não existirem
        if not goals_data:
            goals = {}
        else:
            goals = goals_data[0].goals
            # Se goals for string JSON, converter para dict
            if isinstance(goals, str):
                try:
                    goals = json.loads(goals)
                except:
                    goals = {}
            # Se goals for None, inicializar como dict vazio
            if goals is None:
                goals = {}
        
        # Atualizar meta do mês específico
        # Usar o formato existente: metas_mensais
        if 'metas_mensais' not in goals:
            goals['metas_mensais'] = {}
        
        # Criar entrada para o mês se não existir
        if request.month not in goals['metas_mensais']:
            goals['metas_mensais'][request.month] = {}
        
        # Mapear tipos de meta para o formato existente
        goal_type_mapping = {
            'revenue_goal': 'meta_receita_paga',
            'orders_goal': 'meta_pedidos',
            'conversion_rate_goal': 'meta_taxa_conversao',
            'roas_goal': 'meta_roas',
            'new_customers_goal': 'meta_novos_clientes'
        }
        
        # Usar o mapeamento ou o tipo original se não estiver mapeado
        mapped_goal_type = goal_type_mapping.get(request.goal_type, request.goal_type)
        
        # Salvar a meta no formato existente
        goals['metas_mensais'][request.month][mapped_goal_type] = request.goal_value
        
        # Adicionar metadados para compatibilidade futura
        if 'metadata' not in goals:
            goals['metadata'] = {}
        
        if 'monthly_goals' not in goals['metadata']:
            goals['metadata']['monthly_goals'] = {}
        
        goals['metadata']['monthly_goals'][request.month] = {
            'goal_type': request.goal_type,
            'goal_value': request.goal_value,
            'updated_at': datetime.now().isoformat()
        }
        
        # Converter metas para JSON
        metas_json = json.dumps(goals)
        
        # Query para inserir ou atualizar as metas
        query = f"""
            MERGE `mymetric-hub-shopify.dbt_config.user_goals` AS target
            USING (SELECT '{tablename}' as username, '{metas_json}' as goals) AS source
            ON target.username = source.username
            WHEN MATCHED THEN
                UPDATE SET goals = source.goals, updated_at = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN
                INSERT (username, goals, created_at, updated_at)
                VALUES (source.username, source.goals, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
        """
        
        print(f"Executando query para salvar meta do mês: {query}")
        
        # Executar query
        client.query(query)
        
        return {
            "message": f"Meta do mês {request.month} salva com sucesso",
            "username": tablename,
            "month": request.month,
            "goal_type": request.goal_type,
            "goal_value": request.goal_value
        }
        
    except Exception as e:
        print(f"Erro ao salvar meta do mês: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@admin_router.post("/load-goals", response_model=LoadGoalsResponse)
async def load_goals(
    request: LoadGoalsRequest,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para carregar metas do usuário"""
    
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
            # Usuário com acesso total pode acessar metas de qualquer tabela
            tablename = request.table_name
            print(f"🔓 Usuário com acesso total carregando metas da tabela: {tablename}")
        else:
            # Usuário com acesso limitado só pode acessar metas de sua própria tabela
            if request.table_name != user_tablename:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode acessar metas da tabela '{request.table_name}'"
                )
            tablename = request.table_name
            print(f"🔒 Usuário com acesso limitado carregando metas da tabela: {tablename}")

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
            
            return LoadGoalsResponse(
                success=True,
                message="Metas padrão aplicadas (nenhuma meta configurada encontrada)",
                goals=default_goals,
                username=tablename
            )
        
        # Processar metas encontradas
        goals = goals_data[0].goals
        
        # Se goals for string JSON, converter para dict
        if isinstance(goals, str):
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
        
        return LoadGoalsResponse(
            success=True,
            message="Metas carregadas com sucesso",
            goals=goals,
            username=tablename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao carregar metas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@admin_router.delete("/delete-goal", response_model=DeleteGoalResponse)
async def delete_goal(
    request: DeleteGoalRequest,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para deletar uma meta específica"""
    
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
            # Usuário com acesso total pode deletar metas de qualquer tabela
            tablename = request.table_name
            print(f"🔓 Usuário com acesso total deletando meta da tabela: {tablename}")
        else:
            # Usuário com acesso limitado só pode deletar metas de sua própria tabela
            if request.table_name != user_tablename:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode deletar metas da tabela '{request.table_name}'"
                )
            tablename = request.table_name
            print(f"🔒 Usuário com acesso limitado deletando meta da tabela: {tablename}")

        # Buscar metas existentes
        goals_query = f"""
        SELECT goals
        FROM `mymetric-hub-shopify.dbt_config.user_goals`
        WHERE username = '{tablename}'
        LIMIT 1
        """
        
        goals_result = client.query(goals_query)
        goals_data = list(goals_result.result())
        
        if not goals_data:
            return DeleteGoalResponse(
                success=False,
                message="Nenhuma meta encontrada para deletar",
                deleted_goal=None
            )
        
        # Processar metas encontradas
        goals = goals_data[0].goals
        
        # Se goals for string JSON, converter para dict
        if isinstance(goals, str):
            try:
                goals = json.loads(goals)
            except json.JSONDecodeError:
                goals = {}
        
        if not goals:
            return DeleteGoalResponse(
                success=False,
                message="Nenhuma meta encontrada para deletar",
                deleted_goal=None
            )
        
        # Verificar se existe a meta a ser deletada
        deleted_goal = None
        
        # Mapear tipos de meta para o formato existente
        goal_type_mapping = {
            'revenue_goal': 'meta_receita_paga',
            'orders_goal': 'meta_pedidos',
            'conversion_rate_goal': 'meta_taxa_conversao',
            'roas_goal': 'meta_roas',
            'new_customers_goal': 'meta_novos_clientes'
        }
        
        mapped_goal_type = goal_type_mapping.get(request.goal_type, request.goal_type)
        
        # Verificar se a meta existe em metas_mensais
        if 'metas_mensais' in goals and request.month in goals['metas_mensais']:
            if mapped_goal_type in goals['metas_mensais'][request.month]:
                # Salvar a meta que será deletada para retorno
                deleted_goal = {
                    'month': request.month,
                    'goal_type': request.goal_type,
                    'goal_value': goals['metas_mensais'][request.month][mapped_goal_type]
                }
                
                # Deletar a meta específica
                del goals['metas_mensais'][request.month][mapped_goal_type]
                
                # Se não há mais metas para o mês, remover o mês inteiro
                if not goals['metas_mensais'][request.month]:
                    del goals['metas_mensais'][request.month]
                
                # Se não há mais metas mensais, remover a seção
                if not goals['metas_mensais']:
                    del goals['metas_mensais']
        
        # Verificar se a meta existe em metadata.monthly_goals
        if 'metadata' in goals and 'monthly_goals' in goals['metadata']:
            if request.month in goals['metadata']['monthly_goals']:
                del goals['metadata']['monthly_goals'][request.month]
                
                # Se não há mais metas mensais em metadata, remover a seção
                if not goals['metadata']['monthly_goals']:
                    del goals['metadata']['monthly_goals']
                
                # Se não há mais metadata, remover a seção
                if not goals['metadata']:
                    del goals['metadata']
        
        if not deleted_goal:
            return DeleteGoalResponse(
                success=False,
                message=f"Meta '{request.goal_type}' para o mês '{request.month}' não encontrada",
                deleted_goal=None
            )
        
        # Converter metas atualizadas para JSON
        updated_goals_json = json.dumps(goals)
        
        # Query para atualizar as metas
        update_query = f"""
            UPDATE `mymetric-hub-shopify.dbt_config.user_goals`
            SET goals = '{updated_goals_json}', updated_at = CURRENT_TIMESTAMP()
            WHERE username = '{tablename}'
        """
        
        print(f"🗑️ Executando deleção de meta: {update_query}")
        
        # Executar query de atualização
        client.query(update_query)
        
        return DeleteGoalResponse(
            success=True,
            message=f"Meta '{request.goal_type}' do mês '{request.month}' deletada com sucesso",
            deleted_goal=deleted_goal
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao deletar meta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

