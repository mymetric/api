#!/usr/bin/env python3
"""
Script para configurar o arquivo .env automaticamente
"""

import os
import secrets
from pathlib import Path

def create_env_file():
    """Cria arquivo .env com configurações corretas"""
    env_content = """# Configurações da API
SECRET_KEY=minha_chave_secreta_muito_segura_para_jwt_tokens_2024

# Configurações do Google Cloud/BigQuery
GOOGLE_APPLICATION_CREDENTIALS=credentials/service-account-key.json

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

def check_credentials():
    """Verifica se o arquivo de credenciais existe"""
    cred_file = Path("credentials/service-account-key.json")
    if cred_file.exists():
        print("✅ Arquivo de credenciais encontrado!")
        return True
    else:
        print("❌ Arquivo de credenciais não encontrado!")
        print("   Verifique se o arquivo credentials/service-account-key.json existe")
        return False

def main():
    """Função principal"""
    print("🔧 Configurando ambiente da API...")
    
    # Criar arquivo .env
    create_env_file()
    
    # Verificar credenciais
    check_credentials()
    
    print("\n✅ Configuração concluída!")
    print("📋 Próximos passos:")
    print("1. Execute: python main.py")
    print("2. Acesse: http://localhost:8000/docs")

if __name__ == "__main__":
    main() 