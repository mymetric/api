"""
Utilitários compartilhados entre os módulos
"""

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account
import jwt
from datetime import datetime, timedelta
import secrets
import string
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Carregar variáveis de ambiente
load_dotenv()

# Configurar autenticação
security = HTTPBearer()

# Modelos Pydantic
class TokenData(BaseModel):
    email: Optional[str] = None

class CreateUserRequest(BaseModel):
    email: str
    table_name: str
    admin: bool = False
    access_control: str = "read"  # read, write, full

# Configuração do BigQuery com connection pooling
_bigquery_client = None

def get_bigquery_client():
    """Retorna cliente do BigQuery (singleton com pooling)"""
    global _bigquery_client
    
    if _bigquery_client is None:
        try:
            # Se tiver arquivo de credenciais
            if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                credentials = service_account.Credentials.from_service_account_file(
                    os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                )
                _bigquery_client = bigquery.Client(credentials=credentials)
            else:
                # Usar credenciais padrão
                _bigquery_client = bigquery.Client()
            print("✅ Cliente BigQuery criado com connection pooling")
        except Exception as e:
            print(f"Erro ao conectar com BigQuery: {e}")
            return None
    
    return _bigquery_client

# Thread pool para operações BigQuery assíncronas
# Aumentado para melhor concorrência
bigquery_executor = ThreadPoolExecutor(max_workers=20)

async def execute_bigquery_query_async(query: str, job_config=None):
    """Executa query BigQuery de forma assíncrona com connection pooling"""
    def _run_query():
        client = get_bigquery_client()
        if not client:
            raise Exception("Cliente BigQuery não disponível")
        
        try:
            if job_config:
                result = client.query(query, job_config=job_config)
            else:
                result = client.query(query)
            
            # Usar to_dataframe() ou result() dependendo do tamanho
            return list(result.result())
        except Exception as e:
            print(f"❌ Erro ao executar query BigQuery: {e}")
            raise
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(bigquery_executor, _run_query)

async def execute_bigquery_query_simple_async(query: str):
    """Executa query BigQuery simples de forma assíncrona com connection pooling"""
    def _run_query():
        client = get_bigquery_client()
        if not client:
            raise Exception("Cliente BigQuery não disponível")
        
        try:
            result = client.query(query)
            return list(result.result())
        except Exception as e:
            print(f"❌ Erro ao executar query BigQuery: {e}")
            raise
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(bigquery_executor, _run_query)

# Configurações JWT
SECRET_KEY = os.getenv("SECRET_KEY", "sua_chave_secreta_aqui")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", "sua_chave_refresh_secreta_aqui")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Cria token JWT de acesso"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Cria token JWT de refresh"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifica token JWT de acesso"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token_data = TokenData(email=email)
        return token_data
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

def verify_refresh_token(refresh_token: str):
    """Verifica token JWT de refresh"""
    try:
        payload = jwt.decode(refresh_token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido"
            )
        return email
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido"
        )

def generate_secure_password(length: int = 12) -> str:
    """Gera uma senha segura com caracteres aleatórios"""
    # Caracteres disponíveis para a senha
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    
    # Garantir que a senha tenha pelo menos um de cada tipo
    password = [
        secrets.choice(string.ascii_lowercase),  # Pelo menos uma minúscula
        secrets.choice(string.ascii_uppercase),  # Pelo menos uma maiúscula
        secrets.choice(string.digits),           # Pelo menos um número
        secrets.choice("!@#$%^&*")              # Pelo menos um caractere especial
    ]
    
    # Completar o resto da senha com caracteres aleatórios
    remaining_length = length - len(password)
    password.extend(secrets.choice(characters) for _ in range(remaining_length))
    
    # Embaralhar a senha para não ter padrão previsível
    password_list = list(password)
    secrets.SystemRandom().shuffle(password_list)
    
    return ''.join(password_list)

def verify_admin_user(email: str) -> bool:
    """Verifica se o usuário é admin"""
    try:
        client = get_bigquery_client()
        if not client:
            return False
        
        query = """
        SELECT admin
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
            return False
        
        return results[0].admin
    except Exception as e:
        print(f"Erro ao verificar se usuário é admin: {e}")
        return False 