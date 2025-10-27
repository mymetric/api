import json
import requests
from typing import Optional
import os

class ZAPIService:
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self):
        """Carrega a configuração do Z-API do arquivo JSON"""
        config_path = os.path.join("credentials", "zapi_config.json")
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Arquivo de configuração do Z-API não encontrado: {config_path}")
            return None
        except json.JSONDecodeError:
            print(f"Erro ao decodificar arquivo de configuração do Z-API: {config_path}")
            return None
    
    def send_message(self, message: str, phone: str = "120363322379870288-group") -> bool:
        """
        Envia uma mensagem via Z-API
        
        Args:
            message: Texto da mensagem
            phone: Número do telefone ou grupo (padrão: grupo)
            
        Returns:
            bool: True se a mensagem foi enviada com sucesso, False caso contrário
        """
        if not self.config:
            print("Configuração do Z-API não carregada")
            return False
        
        zapi_payload = {
            "phone": phone,
            "message": message
        }
        
        headers = {
            "Client-Token": self.config["client_token"],
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.config["url"], 
                json=zapi_payload, 
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"Mensagem enviada com sucesso para {phone}")
                return True
            else:
                print(f"Erro ao enviar mensagem. Status: {response.status_code}, Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição para Z-API: {e}")
            return False
        except Exception as e:
            print(f"Erro inesperado ao enviar mensagem: {e}")
            return False
    
    def send_login_notification(self, user_email: str) -> bool:
        """
        Envia notificação de login para o grupo
        
        Args:
            user_email: Email do usuário que fez login
            
        Returns:
            bool: True se a mensagem foi enviada com sucesso
        """
        message = f"🚀 MyMetricHUB 2.0\n\n🔐 Novo login detectado!\n\n👤 Usuário: {user_email}\n⏰ Horário: {self._get_current_time()}"
        
        return self.send_message(message)
    
    def _get_current_time(self) -> str:
        """Retorna a hora atual formatada"""
        from datetime import datetime
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# Instância global do serviço
zapi_service = ZAPIService() 