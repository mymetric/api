from fastapi import FastAPI, HTTPException, Depends, status, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account
import jwt
from datetime import datetime, timedelta
import hashlib

# Importar utilitários e routers
from utils import verify_token, TokenData, get_bigquery_client, create_access_token, create_refresh_token, verify_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, verify_admin_user, generate_secure_password
from email_service import email_service
from metrics import metrics_router
from admin import admin_router
from zapi_service import zapi_service

# Importar métodos customizados
from custom_methods.havaianas_items_scoring import havaianas_router
from better_stack_logger import log_to_better_stack
import time
import json

# Carregar variáveis de ambiente
load_dotenv()

app = FastAPI(
    title="API Dashboard de Métricas",
    description="API para autenticação e dados de métricas",
    version="1.0.0"
)

# Configurar compressão GZip (melhora performance para respostas grandes)
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  # Comprimir apenas respostas maiores que 1KB
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

# Incluir router de admin
app.include_router(admin_router)

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
    users: int
    transactions: int
    revenue: float
    add_to_cart: int
    begin_checkout: int
    add_shipping_info: int
    add_payment_info: int

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


@app.on_event("startup")
async def on_startup_event():
    # Envia um log simples de inicialização (silencioso se não configurado)
    log_to_better_stack(
        message="API started",
        level="info",
        extra={
            "service": "metrics-api",
            "env": os.getenv("ENV", "local"),
        },
    )


@app.middleware("http")
async def better_stack_logging_middleware(request, call_next):
    start_time = time.time()

    # Skip body processing for GET/HEAD requests to improve performance
    request_body_text = None
    if request.method.upper() == "POST":
        try:
            body_bytes = await request.body()
            # Reinject body so downstream handlers can read it again
            async def receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            request._receive = receive

            # Truncate to avoid huge logs
            if body_bytes:
                request_body_text = body_bytes.decode(errors="ignore")
                if len(request_body_text) > 2000:  # Reduced from 4000 to improve performance
                    request_body_text = request_body_text[:2000] + "...<truncated>"
        except Exception:
            request_body_text = None

    # Process request
    response = await call_next(request)

    # Only capture response body for POST requests or errors
    status_code = response.status_code
    media_type = response.media_type
    headers = dict(response.headers)

    # Skip response body processing for GET requests to improve performance
    resp_body_bytes = b""
    response_text = None
    
    if request.method.upper() == "POST" or status_code >= 400:
        try:
            async for chunk in response.body_iterator:
                resp_body_bytes += chunk
            
            # Only decode if it's a POST or error response
            if resp_body_bytes:
                response_text = resp_body_bytes.decode(errors="ignore")
                if len(response_text) > 2000:  # Reduced from 4000
                    response_text = response_text[:2000] + "...<truncated>"
        except Exception:
            # If cannot iterate, keep original response
            return response
        
        # Rebuild response to return to client
        new_response = Response(content=resp_body_bytes, status_code=status_code, headers=headers, media_type=media_type)
    else:
        # For GET requests, return original response without body processing
        new_response = response

    duration_ms = int((time.time() - start_time) * 1000)

    # Sanitize headers (only for POST or errors)
    req_headers = {k: v for k, v in request.headers.items() if k.lower() not in ("authorization", "cookie")}

    # Log to Better Stack (non-blocking best-effort) - only for POST or errors
    if request.method.upper() == "POST" or status_code >= 400:
        try:
            log_to_better_stack(
                message="HTTP POST request" if request.method.upper() == "POST" else "HTTP error",
                level="info",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query": dict(request.query_params),
                    "status": status_code,
                    "duration_ms": duration_ms,
                    "request_headers": req_headers,
                    "request_body": request_body_text if request.method.upper() == "POST" else None,
                    "response_body": response_text,
                },
            )
        except Exception:
            pass

    return new_response

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

        # Registrar timestamp do último login (best-effort, não bloqueia o login)
        try:
            update_query = """
            UPDATE `mymetric-hub-shopify.dbt_config.users`
            SET last_login = CURRENT_TIMESTAMP()
            WHERE email = @email
            """
            update_job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("email", "STRING", user.email),
                ]
            )
            client.query(update_query, job_config=update_job_config).result()
        except Exception as e:
            print(f"Erro ao registrar last_login: {e}")

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
            SELECT email, admin, access_control, tablename as table_name, last_login
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
            SELECT email, admin, access_control, tablename as table_name, last_login
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
                "table_name": row.table_name,
                "last_login": row.last_login.isoformat() if row.last_login else None
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

        # Verificar se o e-mail já existe (o tablename é uma lista CSV, ex.: "surya,gringa").
        # Se já existe, CONCATENA o(s) novo(s) cliente(s) no CSV em vez de tentar um MERGE
        # chaveado em (tablename, email) — que não dá match quando o tablename é diferente
        # e acaba criando uma linha duplicada em vez de consolidar o acesso.
        check_query = """
        SELECT email, tablename FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        LIMIT 1
        """
        check_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", user_data.email),
            ]
        )
        existing = list(client.query(check_query, job_config=check_config).result())

        if existing:
            current_tn = (existing[0].tablename or "").strip()
            if current_tn == "all":
                return {
                    "message": f"Usuário {user_data.email} já tem acesso a todos os clientes (all).",
                    "user": {"email": user_data.email, "table_name": current_tn},
                }
            current_set = [t.strip() for t in current_tn.split(",") if t.strip()]
            add_set = [t.strip() for t in user_data.table_name.split(",") if t.strip()]
            merged = current_set + [t for t in add_set if t not in current_set]
            new_tn = ",".join(merged)

            update_query = """
            UPDATE `mymetric-hub-shopify.dbt_config.users`
            SET tablename = @tablename,
                admin = @admin,
                access_control = @access_control
            WHERE email = @email
            """
            update_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("tablename", "STRING", new_tn),
                    bigquery.ScalarQueryParameter("admin", "BOOL", user_data.admin),
                    bigquery.ScalarQueryParameter("access_control", "STRING", user_data.access_control),
                    bigquery.ScalarQueryParameter("email", "STRING", user_data.email),
                ]
            )
            client.query(update_query, job_config=update_config).result()

            return {
                "message": f"Cliente(s) adicionado(s) ao usuário {user_data.email}. Agora: {new_tn}",
                "user": {
                    "email": user_data.email,
                    "table_name": new_tn,
                    "admin": user_data.admin,
                    "access_control": user_data.access_control,
                },
            }

        insert_query = """
        INSERT INTO `mymetric-hub-shopify.dbt_config.users` (tablename, email, password, admin, access_control)
        VALUES (@tablename, @email, @password, @admin, @access_control)
        """
        insert_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("tablename", "STRING", user_data.table_name),
                bigquery.ScalarQueryParameter("email", "STRING", user_data.email),
                bigquery.ScalarQueryParameter("password", "STRING", hashed_password),
                bigquery.ScalarQueryParameter("admin", "BOOL", user_data.admin),
                bigquery.ScalarQueryParameter("access_control", "STRING", user_data.access_control),
            ]
        )
        client.query(insert_query, job_config=insert_config).result()

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

@app.post("/forgot-password")
async def forgot_password(request: dict):
    """Endpoint para solicitar recuperação de senha"""
    
    try:
        email = request.get("email")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email é obrigatório"
            )
        
        # Verificar se o email existe no sistema
        client = get_bigquery_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro de conexão com o banco de dados"
            )
        
        # Verificar se o usuário existe
        query = """
        SELECT email
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
            # Por segurança, retornar sucesso mesmo se o email não existir
            return {
                "message": "Se o email existir em nosso sistema, você receberá um email de recuperação",
                "email_sent": True
            }
        
        # Gerar nova senha segura
        new_password = generate_secure_password()

        # Fazer hash da nova senha
        hashed_new_password = hash_password(new_password)

        # Extrair nome do email (parte antes do @)
        user_name = email.split('@')[0].title()

        # Enviar o email ANTES de tocar no banco: se o envio falhar, a senha
        # antiga do usuário continua válida em vez de ser trocada silenciosamente
        # sem ele nunca receber a nova (bug reportado 10/08 e 20/08).
        email_sent = email_service.send_password_recovery_email(
            to_email=email,
            to_name=user_name,
            new_password=new_password
        )

        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao enviar email de recuperação"
            )

        # Só atualiza a senha no banco depois de confirmar o envio do email
        update_query = """
        UPDATE `mymetric-hub-shopify.dbt_config.users`
        SET password = @new_password
        WHERE email = @email
        """

        update_job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("new_password", "STRING", hashed_new_password),
                bigquery.ScalarQueryParameter("email", "STRING", email),
            ]
        )

        update_job = client.query(update_query, update_job_config)
        update_job.result()  # Aguardar conclusão

        return {
            "message": "Email de recuperação enviado com sucesso",
            "email": email,
            "email_sent": True,
            "note": "Verifique sua caixa de entrada e spam. A nova senha foi gerada e enviada."
        }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao processar recuperação de senha: {e}")
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
            COUNT(DISTINCT user_pseudo_id) as users,
            SUM(transactions) as transactions,
            ROUND(SUM(revenue), 2) as revenue,
            SUM(add_to_cart) as add_to_cart,
            SUM(begin_checkout) as begin_checkout,
            SUM(add_shipping_info) as add_shipping_info,
            SUM(add_payment_info) as add_payment_info
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
                users=int(row.users) if row.users is not None else 0,
                transactions=int(row.transactions) if row.transactions is not None else 0,
                revenue=float(row.revenue) if row.revenue is not None else 0.0,
                add_to_cart=int(row.add_to_cart) if row.add_to_cart is not None else 0,
                begin_checkout=int(row.begin_checkout) if row.begin_checkout is not None else 0,
                add_shipping_info=int(row.add_shipping_info) if row.add_shipping_info is not None else 0,
                add_payment_info=int(row.add_payment_info) if row.add_payment_info is not None else 0
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
    import multiprocessing
    
    # Usar variável de ambiente ou detectar automaticamente
    workers = int(os.getenv('WORKERS', min(multiprocessing.cpu_count(), 4)))
    
    print(f"🚀 Iniciando servidor com {workers} workers")
    
    # Quando usar workers > 1, precisa passar como string de importação
    if workers > 1:
        uvicorn.run(
            "main:app",  # String de importação quando usar múltiplos workers
            host="0.0.0.0", 
            port=8000,
            workers=workers,
            timeout_keep_alive=65,
            timeout_graceful_shutdown=30,
            access_log=True,
            log_level="info"
        )
    else:
        uvicorn.run(
            app,  # Objeto direto quando usar apenas 1 worker
            host="0.0.0.0", 
            port=8000,
            timeout_keep_alive=65,
            timeout_graceful_shutdown=30,
            access_log=True,
            log_level="info"
        )
