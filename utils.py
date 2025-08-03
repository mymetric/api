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

# Carregar variáveis de ambiente
load_dotenv()

# Configurar autenticação
security = HTTPBearer()

# Modelos Pydantic
class TokenData(BaseModel):
    email: Optional[str] = None

# Configuração do BigQuery
def get_bigquery_client():
    """Retorna cliente do BigQuery"""
    try:
        # Se tiver arquivo de credenciais
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            credentials = service_account.Credentials.from_service_account_file(
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            )
            return bigquery.Client(credentials=credentials)
        else:
            # Usar credenciais padrão
            return bigquery.Client()
    except Exception as e:
        print(f"Erro ao conectar com BigQuery: {e}")
        return None

# Configurações JWT
SECRET_KEY = os.getenv("SECRET_KEY", "sua_chave_secreta_aqui")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Cria token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifica token JWT"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
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