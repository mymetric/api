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

@app.get("/users", response_model=List[User])
async def get_users(token: TokenData = Depends(verify_token)):
    """Endpoint para buscar todos os usuários (apenas admin)"""
    client = get_bigquery_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de conexão com o banco de dados"
        )
    
    try:
        # Verificar se o usuário é admin
        query_admin = f"""
        SELECT admin
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", token.email),
            ]
        )
        
        query_job = client.query(query_admin, job_config=job_config)
        admin_result = list(query_job.result())
        
        if not admin_result or not admin_result[0].admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado - Apenas administradores"
            )
        
        # Buscar todos os usuários
        query = f"""
        SELECT
            email,
            admin,
            access_control,
            tablename
        FROM `mymetric-hub-shopify.dbt_config.users`
        """
        
        query_job = client.query(query)
        results = list(query_job.result())
        
        users = []
        for row in results:
            users.append(User(
                email=row.email,
                admin=row.admin,
                access_control=row.access_control if row.access_control else "",
                tablename=row.tablename
            ))
        
        return users
        
    except Exception as e:
        print(f"Erro ao buscar usuários: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
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
    uvicorn.run(app, host="0.0.0.0", port=8000) 