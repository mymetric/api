#!/usr/bin/env python3
"""
Teste simples do MailerSend
"""

import json
import requests

def test_mailersend():
    """Testa o MailerSend diretamente"""
    
    # Carregar configuração
    try:
        with open('credentials/mailersend_config.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Erro ao carregar configuração: {e}")
        return False
    
    api_key = config.get("api_key")
    from_email = config.get("from_email", "accounts@mymetric.app")
    from_name = config.get("from_name", "MyMetric Team")
    
    if not api_key:
        print("❌ API Key não encontrada")
        return False
    
    print(f"✅ API Key: {api_key[:20]}...")
    print(f"✅ Email de origem: {from_email}")
    print(f"✅ Nome de origem: {from_name}")
    
    # Email de teste
    test_email = input("Digite o email para teste: ").strip()
    if not test_email:
        test_email = "teste@exemplo.com"
    
    # Dados do email
    email_data = {
        "from": {
            "email": from_email,
            "name": from_name
        },
        "to": [
            {
                "email": test_email,
                "name": "Usuário Teste"
            }
        ],
        "subject": "Teste MailerSend - MyMetric",
        "text": "Este é um email de teste enviado via MailerSend API do MyMetric.",
        "html": """
        <html>
        <body>
            <h2>🧪 Teste MailerSend</h2>
            <p>Este é um <b>email de teste</b> enviado via MailerSend API do MyMetric.</p>
            <p>Se você recebeu este email, o serviço está funcionando corretamente!</p>
            <hr>
            <p><small>© 2024 MyMetric</small></p>
        </body>
        </html>
        """
    }
    
    # Headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Enviar email
    try:
        print(f"\n📧 Enviando email de teste para: {test_email}")
        
        response = requests.post(
            "https://api.mailersend.com/v1/email",
            headers=headers,
            json=email_data,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 202:
            print("✅ Email enviado com sucesso!")
            print("📬 Verifique a caixa de entrada (e spam) do email informado")
            return True
        else:
            print("❌ Erro ao enviar email")
            return False
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Teste do MailerSend - MyMetric")
    print("=" * 50)
    
    success = test_mailersend()
    
    if success:
        print("\n🎉 Teste concluído com sucesso!")
    else:
        print("\n❌ Teste falhou!")
    
    print("\n" + "=" * 50)
