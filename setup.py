#!/usr/bin/env python3
"""
Script de configuração inicial para a API Dashboard de Métricas
"""

import os
import sys
import hashlib
from pathlib import Path

def create_env_file():
    """Cria arquivo .env com configurações básicas"""
    env_content = """# Configurações da API
SECRET_KEY=sua_chave_secreta_muito_segura_aqui_$(openssl rand -hex 32)

# Configurações do Google Cloud/BigQuery
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json

# Configurações do servidor
HOST=0.0.0.0
PORT=8000
"""
    
    env_file = Path(".env")
    if env_file.exists():
        print("⚠️  Arquivo .env já existe!")
        overwrite = input("Deseja sobrescrever? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("⏭️  Mantendo arquivo .env existente")
            return
    
    with open(".env", "w") as f:
        f.write(env_content)
    print("✅ Arquivo .env criado com sucesso!")

def generate_secret_key():
    """Gera uma chave secreta segura"""
    import secrets
    return secrets.token_hex(32)

def update_secret_key():
    """Atualiza a chave secreta no arquivo .env"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Arquivo .env não encontrado!")
        return
    
    with open(".env", "r") as f:
        content = f.read()
    
    new_secret = generate_secret_key()
    content = content.replace(
        "SECRET_KEY=sua_chave_secreta_muito_segura_aqui",
        f"SECRET_KEY={new_secret}"
    )
    
    with open(".env", "w") as f:
        f.write(content)
    
    print("✅ Chave secreta atualizada!")

def create_sample_user():
    """Cria um usuário de exemplo para teste"""
    print("\n📝 Criando usuário de exemplo...")
    
    email = input("Email do usuário: ").strip()
    if not email:
        print("⏭️  Pulando criação de usuário")
        return
    
    password = input("Senha do usuário: ").strip()
    if not password:
        print("⏭️  Pulando criação de usuário")
        return
    
    admin = input("É administrador? (y/N): ").strip().lower() == 'y'
    access_control = input("Nível de acesso (read/write/full): ").strip() or "read"
    tablename = input("Nome da tabela de métricas: ").strip() or "user_metrics"
    
    # Hash da senha (base64)
    import base64
    hashed_password = base64.b64encode(password.encode()).decode()
    
    # Query SQL para inserir usuário
    sql_query = f"""
-- Query para inserir usuário no BigQuery
INSERT INTO `mymetric-hub-shopify.dbt_config.users` 
(email, admin, access_control, tablename, password)
VALUES 
('{email}', {str(admin).lower()}, '{access_control}', '{tablename}', '{hashed_password}');
"""
    
    print("\n📋 Query SQL gerada:")
    print("=" * 50)
    print(sql_query)
    print("=" * 50)
    print("\n💡 Execute esta query no BigQuery para criar o usuário!")

def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    print("🔍 Verificando dependências...")
    
    required_packages = [
        "fastapi",
        "uvicorn", 
        "google-cloud-bigquery",
        "google-auth",
        "pydantic",
        "python-jose",
        "passlib",
        "python-multipart",
        "python-dotenv"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Dependências faltando: {', '.join(missing_packages)}")
        print("Execute: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ Todas as dependências estão instaladas!")
        return True

def main():
    """Função principal de configuração"""
    print("🚀 Configuração da API Dashboard de Métricas")
    print("=" * 50)
    
    # Verificar dependências
    if not check_dependencies():
        return
    
    # Criar arquivo .env
    print("\n📄 Configurando arquivo .env...")
    create_env_file()
    
    # Atualizar chave secreta
    print("\n🔐 Gerando chave secreta...")
    update_secret_key()
    
    # Criar usuário de exemplo
    print("\n👤 Configuração de usuário de exemplo")
    create_sample_user()
    
    print("\n" + "=" * 50)
    print("✅ Configuração concluída!")
    print("\n📋 Próximos passos:")
    print("1. Configure as credenciais do Google Cloud no arquivo .env")
    print("2. Execute a query SQL no BigQuery para criar o usuário")
    print("3. Execute: python main.py")
    print("4. Acesse: http://localhost:8000/docs")
    print("\n🔧 Para testar: curl -X GET 'http://localhost:8000/'")

if __name__ == "__main__":
    main() 