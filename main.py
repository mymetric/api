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
from utils import verify_token, TokenData, get_bigquery_client, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
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
    tablename: str

class Token(BaseModel):
    access_token: str
    token_type: str

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
            tablename,
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
        
        # Criar token de acesso
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        # Enviar notificação de login via Z-API
        try:
            zapi_service.send_login_notification(user.email)
        except Exception as e:
            print(f"Erro ao enviar notificação de login: {e}")
        
        return {"access_token": access_token, "token_type": "bearer"}
        
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
            tablename
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
            tablename=user.tablename
        )
        
    except Exception as e:
        print(f"Erro ao buscar perfil: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
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