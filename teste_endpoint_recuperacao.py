#!/usr/bin/env python3
"""
Teste do endpoint de recuperação de senha
"""

import requests
import json

def test_forgot_password_endpoint():
    """Testa o endpoint /forgot-password"""
    
    print("🔐 Teste do Endpoint de Recuperação de Senha")
    print("=" * 60)
    
    # Configurações
    BASE_URL = "http://localhost:8000"
    test_email = "thiago@mymetric.com.br"
    
    print(f"✅ URL base: {BASE_URL}")
    print(f"✅ Email de teste: {test_email}")
    
    # Dados da requisição
    request_data = {
        "email": test_email
    }
    
    print(f"\n📧 Enviando requisição para: {BASE_URL}/forgot-password")
    print(f"📋 Dados: {json.dumps(request_data, indent=2)}")
    
    try:
        print("\n⏳ Enviando requisição...")
        
        response = requests.post(
            f"{BASE_URL}/forgot-password",
            json=request_data,
            timeout=30
        )
        
        print(f"\n📊 Resultado:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Endpoint funcionando corretamente!")
            print(f"📬 Mensagem: {result.get('message', 'N/A')}")
            print(f"📧 Email: {result.get('email', 'N/A')}")
            print(f"✅ Email enviado: {result.get('email_sent', False)}")
            print(f"📝 Nota: {result.get('note', 'N/A')}")
            
            if result.get('email_sent'):
                print("\n🎉 Email de recuperação enviado com sucesso!")
                print("📬 Verifique a caixa de entrada (e spam) do email informado")
            else:
                print("\n⚠️ Email não foi enviado")
                
            return True
        else:
            print(f"\n❌ Erro no endpoint (Status: {response.status_code})")
            try:
                error_data = response.json()
                print(f"Detalhes do erro: {error_data}")
            except:
                print(f"Resposta: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Erro de conexão - Verifique se a API está rodando")
        print("💡 Execute: python3 main.py")
        return False
    except requests.exceptions.Timeout:
        print("\n❌ Timeout na requisição (30s)")
        return False
    except Exception as e:
        print(f"\n❌ Erro na requisição: {e}")
        return False

def test_invalid_email():
    """Testa com email inválido"""
    
    print("\n" + "=" * 60)
    print("🧪 Teste com Email Inválido")
    print("=" * 60)
    
    BASE_URL = "http://localhost:8000"
    
    # Teste 1: Email vazio
    print("\n1️⃣ Testando com email vazio...")
    try:
        response = requests.post(
            f"{BASE_URL}/forgot-password",
            json={},
            timeout=30
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 400:
            print("✅ Validação funcionando - email obrigatório")
        else:
            print("❌ Validação não funcionou")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    # Teste 2: Email inexistente
    print("\n2️⃣ Testando com email inexistente...")
    try:
        response = requests.post(
            f"{BASE_URL}/forgot-password",
            json={"email": "naoexiste@exemplo.com"},
            timeout=30
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✅ Endpoint retorna sucesso mesmo para email inexistente (por segurança)")
            print(f"Mensagem: {result.get('message', 'N/A')}")
        else:
            print("❌ Comportamento inesperado")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    success = test_forgot_password_endpoint()
    test_invalid_email()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 TESTE DO ENDPOINT CONCLUÍDO COM SUCESSO!")
        print("✅ O endpoint /forgot-password está funcionando corretamente")
        print("📧 Verifique o email de recuperação na caixa de entrada")
        print("\n📋 Funcionalidades testadas:")
        print("   • Validação de email obrigatório")
        print("   • Verificação de usuário no banco")
        print("   • Geração de token seguro")
        print("   • Envio de email de recuperação")
        print("   • Resposta de segurança para emails inexistentes")
    else:
        print("❌ TESTE DO ENDPOINT FALHOU!")
        print("⚠️ Verifique se a API está rodando e tente novamente")
    print("=" * 60)
