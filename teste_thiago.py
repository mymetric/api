#!/usr/bin/env python3
"""
Teste específico para enviar email para thiago@mymetric.com.br
"""

import requests
import json
from datetime import datetime

def enviar_email_teste():
    """Envia email de teste para thiago@mymetric.com.br"""
    
    print("🧪 Teste do MailerSend - MyMetric")
    print("=" * 50)
    
    # Configuração do MailerSend
    API_KEY = "mlsn.4408e7dcd8ae9cab0468ffd430013cc7b1240beec8ebe85fddd5018f4ee5f19e"
    FROM_EMAIL = "accounts@mymetric.app"
    FROM_NAME = "MyMetric Team"
    
    print(f"✅ API Key: {API_KEY[:20]}...")
    print(f"✅ Email de origem: {FROM_EMAIL}")
    print(f"✅ Nome de origem: {FROM_NAME}")
    
    # Email de destino
    test_email = "thiago@mymetric.com.br"
    print(f"\n📧 Enviando email de teste para: {test_email}")
    
    # Dados do email
    email_data = {
        "from": {
            "email": FROM_EMAIL,
            "name": FROM_NAME
        },
        "to": [
            {
                "email": test_email,
                "name": "Thiago"
            }
        ],
        "subject": "🧪 Teste MailerSend - MyMetric",
        "text": f"""Teste MailerSend - MyMetric

Olá Thiago!

Este é um email de teste enviado via MailerSend API do MyMetric.

Se você recebeu este email, o serviço está funcionando corretamente!

Detalhes do teste:
- Email de origem: {FROM_EMAIL}
- Nome de origem: {FROM_NAME}
- Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
- Destinatário: {test_email}

Este teste confirma que o sistema de email está funcionando corretamente.

© 2024 MyMetric""",
        "html": f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Teste MailerSend</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .success {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Teste MailerSend</h1>
            <p>MyMetric - Serviço de Email</p>
        </div>
        
        <div class="content">
            <h2>Olá Thiago!</h2>
            
            <p>Este é um <b>email de teste</b> enviado via MailerSend API do MyMetric.</p>
            
            <div class="success">
                <h3>✅ Sucesso!</h3>
                <p>Se você recebeu este email, o serviço está funcionando corretamente!</p>
            </div>
            
            <h3>📋 Detalhes do Teste:</h3>
            <ul>
                <li><strong>Email de origem:</strong> {FROM_EMAIL}</li>
                <li><strong>Nome de origem:</strong> {FROM_NAME}</li>
                <li><strong>Destinatário:</strong> {test_email}</li>
                <li><strong>Data/Hora:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</li>
                <li><strong>API:</strong> MailerSend</li>
            </ul>
            
            <p>Este teste confirma que o sistema de email está funcionando corretamente e pode enviar notificações para os usuários.</p>
        </div>
        
        <div class="footer">
            <p>© 2024 MyMetric. Todos os direitos reservados.</p>
            <p>Este é um email de teste automático.</p>
        </div>
    </div>
</body>
</html>"""
    }
    
    # Headers
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Enviar email
    try:
        print("⏳ Aguarde...")
        
        response = requests.post(
            "https://api.mailersend.com/v1/email",
            headers=headers,
            json=email_data,
            timeout=30
        )
        
        print(f"\n📊 Resultado:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 202:
            print("\n✅ Email enviado com sucesso!")
            print("📬 Verifique a caixa de entrada (e spam) do email thiago@mymetric.com.br")
            print("🎉 O MailerSend está funcionando corretamente!")
            return True
        else:
            print(f"\n❌ Erro ao enviar email (Status: {response.status_code})")
            if response.text:
                try:
                    error_data = response.json()
                    print(f"Detalhes do erro: {error_data}")
                except:
                    print(f"Resposta: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n❌ Timeout na requisição (30s)")
        return False
    except requests.exceptions.ConnectionError:
        print("\n❌ Erro de conexão")
        return False
    except Exception as e:
        print(f"\n❌ Erro na requisição: {e}")
        return False

if __name__ == "__main__":
    success = enviar_email_teste()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("✅ O MailerSend está funcionando corretamente")
        print("📧 Verifique o email de teste na caixa de entrada de thiago@mymetric.com.br")
    else:
        print("❌ TESTE FALHOU!")
        print("⚠️ Verifique a configuração e tente novamente")
    print("=" * 50)
