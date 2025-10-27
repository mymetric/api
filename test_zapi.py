#!/usr/bin/env python3
"""
Script de teste para verificar a funcionalidade do Z-API
"""

from zapi_service import zapi_service

def test_zapi_config():
    """Testa se a configuração do Z-API foi carregada corretamente"""
    print("🔧 Testando configuração do Z-API...")
    
    if zapi_service.config:
        print("✅ Configuração carregada com sucesso!")
        print(f"   URL: {zapi_service.config['url']}")
        print(f"   Token: {zapi_service.config['client_token'][:10]}...")
    else:
        print("❌ Erro ao carregar configuração")
        return False
    
    return True

def test_message_send():
    """Testa o envio de uma mensagem de teste"""
    print("\n📱 Testando envio de mensagem...")
    
    test_message = "🧪 Teste de integração Z-API\n\nEste é um teste automático do sistema de notificações."
    
    success = zapi_service.send_message(test_message)
    
    if success:
        print("✅ Mensagem de teste enviada com sucesso!")
    else:
        print("❌ Erro ao enviar mensagem de teste")
    
    return success

def test_login_notification():
    """Testa a notificação de login"""
    print("\n🔐 Testando notificação de login...")
    
    test_email = "teste@exemplo.com"
    success = zapi_service.send_login_notification(test_email)
    
    if success:
        print("✅ Notificação de login enviada com sucesso!")
    else:
        print("❌ Erro ao enviar notificação de login")
    
    return success

if __name__ == "__main__":
    print("🚀 Iniciando testes do Z-API...\n")
    
    # Testar configuração
    config_ok = test_zapi_config()
    
    if config_ok:
        # Testar envio de mensagem
        message_ok = test_message_send()
        
        # Testar notificação de login
        login_ok = test_login_notification()
        
        print(f"\n📊 Resumo dos testes:")
        print(f"   Configuração: {'✅' if config_ok else '❌'}")
        print(f"   Mensagem: {'✅' if message_ok else '❌'}")
        print(f"   Login: {'✅' if login_ok else '❌'}")
        
        if all([config_ok, message_ok, login_ok]):
            print("\n🎉 Todos os testes passaram! Z-API está funcionando corretamente.")
        else:
            print("\n⚠️  Alguns testes falharam. Verifique a configuração.")
    else:
        print("\n❌ Configuração falhou. Verifique o arquivo credentials/zapi_config.json") 