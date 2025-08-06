# 📱 Integração Z-API - Notificações WhatsApp

Este documento descreve a integração com Z-API para envio de notificações automáticas via WhatsApp.

## 🎯 Funcionalidades

### ✅ Implementadas
- **Notificações automáticas de login** - Envio de mensagem quando usuário faz login
- **Configuração flexível** - Arquivo JSON para configuração
- **Tratamento de erros** - Logs detalhados e fallback graceful
- **Testes automatizados** - Script de teste completo

### 🔮 Futuras
- Notificações de logout
- Alertas de sistema
- Relatórios automáticos
- Configuração de múltiplos grupos

## 📋 Configuração

### 1. Arquivo de Configuração
Localização: `credentials/zapi_config.json`

```json
{
    "url": "https://api.z-api.io/instances/3CE918F241E11034C9538A74AFBCE7F1/token/33DD6E993D824A4F6506F9E9/send-text",
    "client_token": "F17a94d2df575407cbb4a62821c0ad5f3S"
}
```

### 2. Variáveis
- `url`: Endpoint da API Z-API para envio de texto
- `client_token`: Token de autenticação do Z-API

## 🔧 Uso

### Envio Automático (Login)
A notificação é enviada automaticamente quando um usuário faz login:

```python
# Em main.py - função login()
zapi_service.send_login_notification(user.email)
```

### Envio Manual
```python
from zapi_service import zapi_service

# Enviar mensagem personalizada
zapi_service.send_message("Sua mensagem aqui")

# Enviar para número específico
zapi_service.send_message("Mensagem", "5511999999999")

# Enviar notificação de login
zapi_service.send_login_notification("usuario@exemplo.com")
```

## 📱 Formato das Mensagens

### Notificação de Login
```
🚀 MyMetricHUB 2.0

🔐 Novo login detectado!

👤 Usuário: usuario@exemplo.com
⏰ Horário: 15/01/2025 14:30:25
```

### Mensagem Personalizada
```python
message = "🧪 Teste de integração Z-API\n\nEste é um teste automático do sistema de notificações."
```

## 🧪 Testes

### Executar Testes Completos
```bash
python3 test_zapi.py
```

### Testes Individuais
```python
from zapi_service import zapi_service

# Testar configuração
print(zapi_service.config)

# Testar envio
success = zapi_service.send_message("Teste")
print(f"Enviado: {success}")

# Testar notificação de login
success = zapi_service.send_login_notification("teste@exemplo.com")
print(f"Notificação: {success}")
```

## 🔍 Logs e Debug

### Logs de Sucesso
```
✅ Configuração carregada com sucesso!
   URL: https://api.z-api.io/instances/...
   Token: F17a94d2df...

📱 Mensagem enviada com sucesso para 120363322379870288-group
```

### Logs de Erro
```
❌ Erro ao carregar configuração
❌ Erro na requisição para Z-API: Connection timeout
❌ Erro ao enviar mensagem. Status: 401, Response: Unauthorized
```

## 🛠️ Troubleshooting

### Problema: Configuração não carregada
**Solução:**
1. Verificar se `credentials/zapi_config.json` existe
2. Validar formato JSON
3. Verificar permissões do arquivo

### Problema: Erro 401 (Unauthorized)
**Solução:**
1. Verificar se o `client_token` está correto
2. Confirmar se a instância está ativa no Z-API
3. Verificar se o token não expirou

### Problema: Timeout na requisição
**Solução:**
1. Verificar conectividade com internet
2. Confirmar se a URL está correta
3. Verificar se o Z-API está online

### Problema: Mensagem não chega no WhatsApp
**Solução:**
1. Verificar se o número/grupo está correto
2. Confirmar se o WhatsApp está conectado
3. Verificar logs do Z-API

## 📊 Monitoramento

### Métricas Importantes
- Taxa de sucesso no envio
- Tempo de resposta da API
- Erros por tipo
- Uso de tokens

### Logs Recomendados
```python
# Adicionar em produção
import logging

logging.info(f"Z-API: Tentativa de envio para {phone}")
logging.info(f"Z-API: Resposta {response.status_code}")
logging.error(f"Z-API: Erro {error}")
```

## 🔒 Segurança

### Boas Práticas
1. **Nunca commitar** tokens no Git
2. **Usar variáveis de ambiente** em produção
3. **Rotacionar tokens** periodicamente
4. **Monitorar uso** da API

### Configuração Segura
```bash
# Em produção, usar variáveis de ambiente
export ZAPI_URL="https://api.z-api.io/..."
export ZAPI_TOKEN="seu_token_aqui"
```

## 📚 Referências

- [Documentação Z-API](https://developer.z-api.io/)
- [API de Envio de Texto](https://developer.z-api.io/apis/send-text)
- [Configuração de Instâncias](https://developer.z-api.io/instances)

## 🤝 Suporte

Para problemas com a integração Z-API:
1. Verificar logs da aplicação
2. Executar `python3 test_zapi.py`
3. Consultar documentação do Z-API
4. Verificar status do serviço Z-API 