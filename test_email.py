#!/usr/bin/env python3
"""
Script de teste para o serviço de email
"""

import requests
import json

# Configurações
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@exemplo.com"
ADMIN_PASSWORD = "123"

def login():
    """Faz login e retorna o token"""
    try:
        response = requests.post(f"{BASE_URL}/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"✅ Login realizado com sucesso para {ADMIN_EMAIL}")
            return token
        else:
            print(f"❌ Erro no login: {response.status_code}")
            print(f"Detalhes: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro na requisição de login: {e}")
        return None

def test_email_service(token, test_email):
    """Testa o serviço de email"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        email_data = {
            "to_email": test_email,
            "to_name": "Usuário Teste"
        }
        
        response = requests.post(f"{BASE_URL}/test-email", 
                               json=email_data, 
                               headers=headers)
        
        if response.status_code == 200:
            print(f"✅ Email de teste enviado com sucesso para {test_email}")
            print(f"Resposta: {response.json()}")
            return True
        else:
            print(f"❌ Erro ao enviar email de teste: {response.status_code}")
            print(f"Detalhes: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar email: {e}")
        return False

def create_user_with_email(token, user_data):
    """Cria usuário e verifica se o email foi enviado"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.post(f"{BASE_URL}/create-user", 
                               json=user_data, 
                               headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Usuário criado com sucesso: {user_data['email']}")
            print(f"Senha gerada: {result['generated_password']}")
            print(f"Email enviado: {result['email_sent']}")
            return result
        else:
            print(f"❌ Erro ao criar usuário: {response.status_code}")
            print(f"Detalhes: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erro ao criar usuário: {e}")
        return None

if __name__ == "__main__":
    print("🧪 Testando Serviço de Email - MyMetric")
    print("=" * 50)
    
    # 1. Login como admin
    print("\n1️⃣ Fazendo login como administrador...")
    token = login()
    if not token:
        print("❌ Não foi possível fazer login. Abortando testes.")
        exit(1)
    
    # 2. Testar envio de email
    print("\n2️⃣ Testando serviço de email...")
    test_email = input("Digite um email para teste: ").strip()
    
    if test_email:
        test_email_service(token, test_email)
    else:
        print("⏭️ Pulando teste de email")
    
    # 3. Criar usuário com envio de email
    print("\n3️⃣ Criando usuário com envio de email...")
    user_data = {
        "email": "teste@exemplo.com",
        "table_name": "test_metrics",
        "access_control": "read",
        "admin": False
    }
    
    result = create_user_with_email(token, user_data)
    
    if result:
        print("\n🎉 Teste concluído com sucesso!")
        print(f"✅ Usuário criado: {result['user']['email']}")
        print(f"✅ Email enviado: {result['email_sent']}")
        print(f"✅ Senha gerada: {result['generated_password']}")
    else:
        print("\n❌ Teste falhou!")
    
    print("\n" + "=" * 50)
    print("📧 Verifique a caixa de entrada do email de teste!")
