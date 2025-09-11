from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account
import jwt
from datetime import datetime, timedelta
import hashlib

# Importar utilitários e router de métricas
from utils import verify_token, TokenData, get_bigquery_client, create_access_token, create_refresh_token, verify_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, verify_admin_user, generate_secure_password
from email_service import email_service
from metrics import metrics_router
from zapi_service import zapi_service

# Importar métodos customizados
from custom_methods.havaianas_items_scoring import havaianas_router

# Carregar variáveis de ambiente
load_dotenv()

app = FastAPI(
    title="API Dashboard de Métricas",
    description="API para autenticação e dados de métricas",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir router de métricas
app.include_router(metrics_router)

# Incluir router de métodos customizados
app.include_router(havaianas_router)

# Configurar autenticação
security = HTTPBearer()

# Modelos Pydantic
class UserLogin(BaseModel):
    email: str
    password: str

class User(BaseModel):
    email: str
    admin: bool
    access_control: str  # Corrigido para STRING
    table_name: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    table_name: str
    access_control: str
    admin: bool

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ExperimentData(BaseModel):
    event_date: str
    experiment_id: str
    experiment_name: str
    experiment_variant: str
    category: str
    sessions: int
    transactions: int
    revenue: float

class ExperimentQuery(BaseModel):
    table_name: str
    start_date: str
    end_date: str

class CreateUserRequest(BaseModel):
    email: str
    table_name: str
    access_control: str = "read"  # read, write, full
    admin: bool = False

def hash_password(password: str) -> str:
    """Converte a senha para base64"""
    import base64
    return base64.b64encode(password.encode()).decode()

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {"message": "API Dashboard de Métricas - Funcionando!"}

@app.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """Endpoint para login de usuários"""
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        # Query para buscar usuário
        query = f"""
        SELECT
            email,
            admin,
            access_control,
            tablename as table_name,
            password
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", user_credentials.email),
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )
        
        user = results[0]
        hashed_password = hash_password(user_credentials.password)
        
        # Debug: imprimir informações para debug
        print(f"Debug - Email: {user.email}")
        print(f"Debug - Senha fornecida (hash): {hashed_password}")
        print(f"Debug - Senha no BD: {user.password}")
        print(f"Debug - Senhas iguais: {user.password == hashed_password}")
        
        # Verificar senha
        if user.password != hashed_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )
        
        # Criar tokens de acesso e refresh
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        refresh_token = create_refresh_token(
            data={"sub": user.email}, expires_delta=refresh_token_expires
        )
        
        # Enviar notificação de login via Z-API
        try:
            zapi_service.send_login_notification(user.email)
        except Exception as e:
            print(f"Erro ao enviar notificação de login: {e}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "table_name": user.table_name,
            "access_control": user.access_control if user.access_control else "read",
            "admin": user.admin
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Erro no login: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@app.post("/refresh-token", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """Endpoint para renovar access token usando refresh token"""
    try:
        # Verificar se o refresh token é válido
        email = verify_refresh_token(request.refresh_token)
        
        # Buscar dados do usuário no banco
        client = get_bigquery_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro de conexão com o banco de dados"
            )
        
        # Query para buscar dados do usuário
        query = f"""
        SELECT
            email,
            admin,
            access_control,
            tablename as table_name
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", email),
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado"
            )
        
        user = results[0]
        
        # Criar novos tokens
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        new_access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        new_refresh_token = create_refresh_token(
            data={"sub": user.email}, expires_delta=refresh_token_expires
        )
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "table_name": user.table_name,
            "access_control": user.access_control if user.access_control else "read",
            "admin": user.admin
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Erro no refresh token: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@app.get("/users")
async def list_users(
    table_name: Optional[str] = None,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para listar usuários (apenas admins)"""
    
    # Verificar se o usuário logado é admin
    if not verify_admin_user(token.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem listar usuários"
        )
    
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        # Construir query com filtro opcional
        if table_name:
            query = """
            SELECT email, admin, access_control, tablename as table_name
            FROM `mymetric-hub-shopify.dbt_config.users`
            WHERE tablename = @table_name
            ORDER BY email
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("table_name", "STRING", table_name),
                ]
            )
            
            query_job = client.query(query, job_config=job_config)
        else:
            query = """
            SELECT email, admin, access_control, tablename as table_name
            FROM `mymetric-hub-shopify.dbt_config.users`
            ORDER BY email
            """
            
            query_job = client.query(query)
        
        results = list(query_job.result())
        
        users = []
        for row in results:
            users.append({
                "email": row.email,
                "admin": row.admin,
                "access_control": row.access_control,
                "table_name": row.table_name
            })
        
        return {
            "users": users,
            "total": len(users),
            "filtered_by": table_name if table_name else "all"
        }
        
    except Exception as e:
        print(f"Erro ao listar usuários: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@app.delete("/users/{email}")
async def delete_user(email: str, token: TokenData = Depends(verify_token)):
    """Endpoint para deletar usuários (apenas admins)"""
    
    # Verificar se o usuário logado é admin
    if not verify_admin_user(token.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem deletar usuários"
        )
    
    # Não permitir que o admin se delete a si mesmo
    if email == token.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível deletar o próprio usuário"
        )
    
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        query = f"""
        DELETE FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", email),
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        query_job.result()  # Aguardar conclusão
        
        return {"message": f"Usuário {email} deletado com sucesso"}
        
    except Exception as e:
        print(f"Erro ao deletar usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@app.post("/create-user")
async def create_user(
    user_data: CreateUserRequest,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para criação de usuários (apenas admins)"""
    
    # Verificar se o usuário logado é admin
    if not verify_admin_user(token.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem criar usuários"
        )
    
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        # Gerar senha segura automaticamente
        generated_password = generate_secure_password()
        hashed_password = hash_password(generated_password)
        
        # Query para inserir/atualizar usuário usando MERGE
        query = f"""
        MERGE `mymetric-hub-shopify.dbt_config.users` AS target
        USING (SELECT '{user_data.table_name}' as tablename, '{user_data.email}' as email, '{hashed_password}' as password) AS source
        ON target.tablename = source.tablename AND target.email = source.email
        WHEN MATCHED THEN
            UPDATE SET 
                email = source.email, 
                password = source.password, 
                admin = {str(user_data.admin).lower()},
                access_control = '{user_data.access_control}'
        WHEN NOT MATCHED THEN
            INSERT (tablename, email, password, admin, access_control)
            VALUES ('{user_data.table_name}', '{user_data.email}', '{hashed_password}', {str(user_data.admin).lower()}, '{user_data.access_control}')
        """
        
        # Executar query
        query_job = client.query(query)
        query_job.result()  # Aguardar conclusão
        
        # Enviar email com as credenciais
        email_sent = False
        try:
            # Extrair nome do email (parte antes do @)
            user_name = user_data.email.split('@')[0].title()
            
            email_sent = email_service.send_user_creation_email(
                to_email=user_data.email,
                to_name=user_name,
                generated_password=generated_password,
                table_name=user_data.table_name,
                access_control=user_data.access_control
            )
        except Exception as e:
            print(f"⚠️ Erro ao enviar email: {e}")
            email_sent = False
        
        return {
            "message": "Usuário criado/atualizado com sucesso",
            "user": {
                "email": user_data.email,
                "table_name": user_data.table_name,
                "admin": user_data.admin,
                "access_control": user_data.access_control
            },
            "generated_password": generated_password,
            "note": "Esta senha foi gerada automaticamente e só será exibida uma vez. Guarde-a em local seguro.",
            "email_sent": email_sent
        }
        
    except Exception as e:
        print(f"Erro ao criar usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@app.get("/profile")
async def get_profile(token: TokenData = Depends(verify_token)):
    """Endpoint para buscar perfil do usuário logado"""
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        query = f"""
        SELECT
            email,
            admin,
            access_control,
            tablename as table_name
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", token.email),
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user = results[0]
        return User(
            email=user.email,
            admin=user.admin,
            access_control=user.access_control if user.access_control else "",
            table_name=user.table_name
        )
        
    except Exception as e:
        print(f"Erro ao buscar perfil: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@app.post("/test-email")
async def test_email(
    email_data: dict,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para testar envio de email (apenas admins)"""
    
    # Verificar se o usuário logado é admin
    if not verify_admin_user(token.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem testar emails"
        )
    
    try:
        to_email = email_data.get("to_email")
        to_name = email_data.get("to_name", "Teste")
        
        if not to_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email de destino é obrigatório"
            )
        
        # Enviar email de teste
        email_sent = email_service.send_test_email(to_email, to_name)
        
        if email_sent:
            return {
                "message": "Email de teste enviado com sucesso",
                "to_email": to_email,
                "to_name": to_name
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao enviar email de teste"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao testar email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@app.post("/metrics/experiments", response_model=List[ExperimentData])
async def get_experiment_data(
    query_params: ExperimentQuery,
    token: TokenData = Depends(verify_token)
):
    """Endpoint para buscar dados de experimentos"""
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        # Query para buscar dados de experimentos
        # Constrói o nome da tabela usando o nome do cliente + sufixo fixo
        table_name = f"dbt_join.{query_params.table_name}_experiment_impressions_results"
        
        # Primeiro verificar se a tabela existe
        check_table_query = f"""
        SELECT COUNT(*) as table_exists
        FROM `{table_name}`
        LIMIT 1
        """
        
        try:
            check_job = client.query(check_table_query)
            check_results = list(check_job.result())
            print(f"Tabela {table_name} encontrada e acessível")
        except Exception as e:
            print(f"Erro ao acessar tabela {table_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tabela {table_name} não encontrada ou não acessível"
            )
        
        query = f"""
        SELECT
            event_date,
            experiment_id,
            experiment_name,
            experiment_variant,
            category,
            COUNT(DISTINCT CONCAT(user_pseudo_id, ga_session_id)) as sessions,
            SUM(transactions) as transactions,
            ROUND(SUM(revenue), 2) as revenue
        FROM `{table_name}`
        WHERE event_date BETWEEN @start_date AND @end_date
        GROUP BY 
            event_date,
            experiment_id,
            experiment_name,
            experiment_variant,
            category
        ORDER BY revenue DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "STRING", query_params.start_date),
                bigquery.ScalarQueryParameter("end_date", "STRING", query_params.end_date),
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        # Converter resultados para o modelo Pydantic
        experiment_data = []
        for row in results:
            experiment_data.append(ExperimentData(
                event_date=str(row.event_date) if row.event_date else "",
                experiment_id=str(row.experiment_id) if row.experiment_id else "",
                experiment_name=str(row.experiment_name) if row.experiment_name else "",
                experiment_variant=str(row.experiment_variant) if row.experiment_variant else "",
                category=str(row.category) if row.category else "",
                sessions=int(row.sessions) if row.sessions is not None else 0,
                transactions=int(row.transactions) if row.transactions is not None else 0,
                revenue=float(row.revenue) if row.revenue is not None else 0.0
            ))
        
        return experiment_data
        
    except Exception as e:
        print(f"Erro ao buscar dados de experimentos: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        timeout_keep_alive=65,  # Manter conexão viva por 65s
        timeout_graceful_shutdown=30  # Tempo para shutdown gracioso
    )
