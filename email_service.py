"""
Serviço de email usando AWS SES (SMTP). Remetente em mymetric.app.
Migrado do MailerSend (conta bloqueada) em 24/08/2026.
"""

import json
import os
import ssl
import smtplib
from email.message import EmailMessage
from typing import Optional, Dict, Any

class EmailService:
    def __init__(self):
        self.config = self._load_config()
        self.from_email = self.config.get("from_email", "accounts@mymetric.app")
        self.from_name = self.config.get("from_name", "MyMetric Team")
        # AWS SES SMTP (us-east-1). Credenciais IAM SMTP; qualquer identidade
        # verificada na conta pode ser o remetente (mymetric.app está verificado).
        self.smtp_host = self.config.get("smtp_host") or os.getenv("SES_SMTP_HOST", "email-smtp.us-east-1.amazonaws.com")
        self.smtp_port = int(self.config.get("smtp_port") or os.getenv("SES_SMTP_PORT", "587"))
        self.smtp_user = self.config.get("smtp_user") or os.getenv("SES_SMTP_USER")
        self.smtp_pass = self.config.get("smtp_pass") or os.getenv("SES_SMTP_PASS")
        # mantido só pros guards existentes (True = e-mail configurado)
        self.api_key = self.smtp_user

    def _load_config(self) -> Dict[str, Any]:
        """Carrega config de e-mail (SES). Fallback: mailersend_config só p/ from_email/name."""
        for path in ("credentials/ses_config.json", "credentials/mailersend_config.json"):
            try:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        return json.load(f)
            except Exception as e:
                print(f"❌ Erro ao carregar {path}: {e}")
        print("⚠️ Config de e-mail não encontrada (usando env/defaults do SES)")
        return {}

    def _deliver(self, email_data: Dict[str, Any]) -> bool:
        """Envia via AWS SES (SMTP). HTML SEMPRE em base64 (o SES corrompe
        quoted-printable ao reescrever links/pixel). Ver reference_mymetric_email_platform."""
        if not self.smtp_user or not self.smtp_pass:
            print("❌ Credenciais SES (SES_SMTP_USER/PASS) não configuradas")
            return False
        frm = email_data.get("from", {})
        dest = email_data.get("to", [{}])[0]
        to_email = dest.get("email")
        try:
            msg = EmailMessage()
            msg["From"] = f"{frm.get('name', self.from_name)} <{frm.get('email', self.from_email)}>"
            msg["To"] = f"{dest.get('name')} <{to_email}>" if dest.get("name") else to_email
            msg["Subject"] = email_data.get("subject", "")
            msg.set_content(email_data.get("text", "") or " ")
            html = email_data.get("html")
            if html:
                msg.add_alternative(html, subtype="html", cte="base64")
            s = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            s.ehlo(); s.starttls(context=ssl.create_default_context()); s.ehlo()
            s.login(self.smtp_user, self.smtp_pass)
            s.send_message(msg)
            s.quit()
            print(f"✅ Email enviado (SES) para {to_email}")
            return True
        except Exception as e:
            print(f"❌ Erro ao enviar email (SES) para {to_email}: {e}")
            return False

    def send_user_creation_email(
        self, 
        to_email: str, 
        to_name: str, 
        generated_password: str,
        table_name: str,
        access_control: str
    ) -> bool:
        """Envia email de criação de usuário"""
        try:
            if not self.api_key:
                print("❌ Chave da API do MailerSend não configurada")
                return False
            
            subject = "Acesso ao MyMetricHUB - MyMetric"
            
            # Template HTML do email
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Acesso MyMetric</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .credentials {{ background: #fff; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #667eea; }}
                    .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                    .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚀 MyMetricHUB</h1>
                        <p>Seu acesso foi criado com sucesso!</p>
                    </div>
                    
                    <div class="content">
                        <h2>Olá, {to_name}!</h2>
                        
                        <p>Seu acesso foi criado com sucesso.</p>
                        
                        <div class="credentials">
                            <h3>📋 Credenciais de Acesso</h3>
                            <p><strong>Email:</strong> {to_email}</p>
                            <p><strong>Senha:</strong> <code style="background: #f1f1f1; padding: 5px 10px; border-radius: 4px; font-family: monospace;">{generated_password}</code></p>
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
            </html>
            """
            
            # Template de texto simples
            text_content = f"""
            Acesso ao MyMetricHUB - MyMetric
            
            Olá, {to_name}!
            
            Seu acesso foi criado com sucesso.
            
            CREDENCIAIS DE ACESSO:
            - Email: {to_email}
            - Senha: {generated_password}
            - URL: https://beta.mymetric.app
            
            
            Se você tiver alguma dúvida ou precisar de suporte, entre em contato com nossa equipe.
            
            © 2024 MyMetric. Todos os direitos reservados.
            """
            
            # Dados para envio
            email_data = {
                "from": {
                    "email": self.from_email,
                    "name": self.from_name
                },
                "to": [
                    {
                        "email": to_email,
                        "name": to_name
                    }
                ],
                "subject": subject,
                "text": text_content,
                "html": html_content
            }
            
            # Enviar via AWS SES (SMTP)
            return self._deliver(email_data)

        except Exception as e:
            print(f"❌ Erro ao enviar email: {e}")
            return False
    
    def send_password_recovery_email(
        self, 
        to_email: str, 
        to_name: str, 
        new_password: str
    ) -> bool:
        """Envia email de recuperação de senha"""
        try:
            if not self.api_key:
                print("❌ Chave da API do MailerSend não configurada")
                return False
            
            subject = "Nova Senha - MyMetricHUB"
            
            # Template HTML do email
            html_content = f"""
            <!DOCTYPE html>
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
            </html>
            """
            
            # Template de texto simples
            text_content = f"""
            Nova Senha - MyMetricHUB
            
            Olá, {to_name}!
            
            Uma nova senha foi gerada para sua conta.
            
            CREDENCIAIS DE ACESSO:
            - Email: {to_email}
            - Nova Senha: {new_password}
            - URL: https://beta.mymetric.app
            
            
            Se você tiver alguma dúvida ou precisar de suporte, entre em contato com nossa equipe.
            
            © 2024 MyMetric. Todos os direitos reservados.
            """
            
            # Dados para envio
            email_data = {
                "from": {
                    "email": self.from_email,
                    "name": self.from_name
                },
                "to": [
                    {
                        "email": to_email,
                        "name": to_name
                    }
                ],
                "subject": subject,
                "text": text_content,
                "html": html_content
            }
            
            # Enviar via AWS SES (SMTP)
            return self._deliver(email_data)

        except Exception as e:
            print(f"❌ Erro ao enviar email de recuperação: {e}")
            return False

    def send_test_email(self, to_email: str, to_name: str) -> bool:
        """Envia email de teste"""
        try:
            if not self.api_key:
                print("❌ Chave da API do MailerSend não configurada")
                return False
            
            email_data = {
                "from": {
                    "email": self.from_email,
                    "name": self.from_name
                },
                "to": [
                    {
                        "email": to_email,
                        "name": to_name
                    }
                ],
                "subject": "Teste de Email - MyMetric",
                "text": "Este é um email de teste enviado via MailerSend API do MyMetric.",
                "html": "<p>Este é um <b>email de teste</b> enviado via MailerSend API do MyMetric.</p>"
            }
            
            return self._deliver(email_data)

        except Exception as e:
            print(f"❌ Erro ao enviar email de teste: {e}")
            return False

# Instância global do serviço de email
email_service = EmailService()
