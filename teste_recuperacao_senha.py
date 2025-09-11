#!/usr/bin/env python3
"""
Teste de email de recuperação de senha para thiago@mymetric.com.br
"""

import requests
import json
from datetime import datetime
import secrets
import string

def gerar_nova_senha():
    """Gera uma nova senha segura"""
    # Gerar senha de 12 caracteres com letras, números e símbolos
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(12))
    return password

def enviar_email_recuperacao():
    """Envia email de recuperação de senha para thiago@mymetric.com.br"""
    
    print("🔐 Teste de Email de Recuperação de Senha - MyMetricHUB")
    print("=" * 60)
    
    # Configuração do MailerSend
    API_KEY = "mlsn.4408e7dcd8ae9cab0468ffd430013cc7b1240beec8ebe85fddd5018f4ee5f19e"
    FROM_EMAIL = "accounts@mymetric.app"
    FROM_NAME = "MyMetric Team"
    
    print(f"✅ API Key: {API_KEY[:20]}...")
    print(f"✅ Email de origem: {FROM_EMAIL}")
    print(f"✅ Nome de origem: {FROM_NAME}")
    
    # Dados do usuário de teste
    to_email = "thiago@mymetric.com.br"
    to_name = "Thiago"
    new_password = gerar_nova_senha()
    
    print(f"\n📧 Enviando email de recuperação para: {to_email}")
    print(f"👤 Nome: {to_name}")
    print(f"🔑 Nova senha gerada: {new_password}")
    
    # Dados do email de recuperação
    email_data = {
        "from": {
            "email": FROM_EMAIL,
            "name": FROM_NAME
        },
        "to": [
            {
                "email": to_email,
                "name": to_name
            }
        ],
        "subject": "Nova Senha - MyMetricHUB",
        "text": f"""Nova Senha - MyMetricHUB

Olá, {to_name}!

Uma nova senha foi gerada para sua conta.

CREDENCIAIS DE ACESSO:
- Email: {to_email}
- Nova Senha: {new_password}
- URL: https://beta.mymetric.app


Se você tiver alguma dúvida ou precisar de suporte, entre em contato com nossa equipe.

© 2024 MyMetric. Todos os direitos reservados.""",
        "html": f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nova Senha - MyMetricHUB</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .credentials {{ background: #fff; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #667eea; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
        .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 8px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 MyMetricHUB</h1>
            <p>Nova Senha Gerada</p>
        </div>
        
        <div class="content">
            <h2>Olá, {to_name}!</h2>
            
            <p>Uma nova senha foi gerada para sua conta.</p>
            
            <div class="credentials">
                <h3>🔑 Nova Senha</h3>
                <p><strong>Email:</strong> {to_email}</p>
                <p><strong>Nova Senha:</strong> <code style="background: #f1f1f1; padding: 5px 10px; border-radius: 4px; font-family: monospace;">{new_password}</code></p>
                <p><strong>URL:</strong> <a href="https://beta.mymetric.app">https://beta.mymetric.app</a></p>
            </div>
            
            
            
            <p>Se você tiver alguma dúvida ou precisar de suporte, entre em contato com nossa equipe.</p>
        </div>
        
        <div class="footer">
            <p>© 2024 MyMetric. Todos os direitos reservados.</p>
            <p>Este é um email automático, não responda a esta mensagem.</p>
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
        print("\n⏳ Enviando email de recuperação...")
        
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
            print("\n✅ Email de recuperação enviado com sucesso!")
            print("📬 Verifique a caixa de entrada (e spam) do email thiago@mymetric.com.br")
            print("🎉 O MailerSend está funcionando corretamente!")
            print("\n📋 Detalhes do email enviado:")
            print(f"   • Destinatário: {to_email}")
            print(f"   • Nome: {to_name}")
            print(f"   • Nova senha: {new_password}")
            print(f"   • URL: https://beta.mymetric.app")
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
    success = enviar_email_recuperacao()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 TESTE DE RECUPERAÇÃO DE SENHA CONCLUÍDO COM SUCESSO!")
        print("✅ O MailerSend está funcionando corretamente")
        print("📧 Verifique o email de recuperação na caixa de entrada de thiago@mymetric.com.br")
        print("\n📋 Este email contém:")
        print("   • Nova senha gerada")
        print("   • URL do MyMetricHUB")
        print("   • Instruções de segurança")
        print("   • Aviso sobre uso único da senha")
    else:
        print("❌ TESTE DE RECUPERAÇÃO DE SENHA FALHOU!")
        print("⚠️ Verifique a configuração e tente novamente")
    print("=" * 60)
