#!/usr/bin/env python3
"""
Script de teste direto para o MailerSend
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from email_service import EmailService

def test_mailersend_config():
    """Testa se a configuração do MailerSend está correta"""
    print("🔧 Verificando configuração do MailerSend...")
    
    email_service = EmailService()
    
    if not email_service.api_key:
        print("❌ API Key não encontrada")
        return False
    
    if not email_service.from_email:
        print("❌ Email de origem não configurado")
        return False
    
    print(f"✅ API Key: {email_service.api_key[:20]}...")
    print(f"✅ Email de origem: {email_service.from_email}")
    print(f"✅ Nome de origem: {email_service.from_name}")
    print(f"✅ URL base: {email_service.base_url}")
    
    return True

def test_simple_email():
    """Testa envio de email simples"""
    print("\n📧 Testando envio de email simples...")
    
    email_service = EmailService()
    
    # Email de teste - você pode alterar aqui
    test_email = input("Digite o email para teste (ou pressione Enter para usar teste@exemplo.com): ").strip()
    if not test_email:
        test_email = "teste@exemplo.com"
    
    test_name = input("Digite o nome para teste (ou pressione Enter para usar 'Usuário Teste'): ").strip()
    if not test_name:
        test_name = "Usuário Teste"
    
    print(f"Enviando email de teste para: {test_email}")
    
    success = email_service.send_test_email(test_email, test_name)
    
    if success:
        print("✅ Email de teste enviado com sucesso!")
        print("📬 Verifique a caixa de entrada (e spam) do email informado")
    else:
        print("❌ Falha ao enviar email de teste")
    
    return success

def test_user_creation_email():
    """Testa envio de email de criação de usuário"""
    print("\n👤 Testando envio de email de criação de usuário...")
    
    email_service = EmailService()
    
    # Dados de teste
    test_email = input("Digite o email para teste (ou pressione Enter para usar teste@exemplo.com): ").strip()
    if not test_email:
        test_email = "teste@exemplo.com"
    
    test_name = input("Digite o nome para teste (ou pressione Enter para usar 'Usuário Teste'): ").strip()
    if not test_name:
        test_name = "Usuário Teste"
    
    generated_password = "TempPass123!"
    table_name = "test_metrics"
    access_control = "read"
    
    print(f"Enviando email de criação de usuário para: {test_email}")
    print(f"Senha gerada: {generated_password}")
    print(f"Tabela: {table_name}")
    print(f"Permissões: {access_control}")
    
    success = email_service.send_user_creation_email(
        to_email=test_email,
        to_name=test_name,
        generated_password=generated_password,
        table_name=table_name,
        access_control=access_control
    )
    
    if success:
        print("✅ Email de criação de usuário enviado com sucesso!")
        print("📬 Verifique a caixa de entrada (e spam) do email informado")
    else:
        print("❌ Falha ao enviar email de criação de usuário")
    
    return success

def main():
    """Função principal"""
    print("🧪 Teste do MailerSend - MyMetric")
    print("=" * 50)
    
    # 1. Verificar configuração
    if not test_mailersend_config():
        print("\n❌ Configuração inválida. Verifique o arquivo mailersend_config.json")
        return
    
    # 2. Testar email simples
    print("\n" + "=" * 50)
    test_simple = test_simple_email()
    
    # 3. Testar email de criação de usuário
    print("\n" + "=" * 50)
    test_user = test_user_creation_email()
    
    # 4. Resumo dos testes
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES:")
    print(f"✅ Configuração: OK")
    print(f"{'✅' if test_simple else '❌'} Email simples: {'OK' if test_simple else 'FALHOU'}")
    print(f"{'✅' if test_user else '❌'} Email criação usuário: {'OK' if test_user else 'FALHOU'}")
    
    if test_simple and test_user:
        print("\n🎉 Todos os testes passaram! O MailerSend está funcionando corretamente.")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique os logs acima para mais detalhes.")
    
    print("\n📧 Lembre-se de verificar a caixa de entrada (e spam) dos emails de teste!")

if __name__ == "__main__":
    main()
