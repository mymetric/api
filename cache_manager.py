"""
Gerenciador de cache para dados básicos
"""

import time
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class CacheManager:
    """Gerenciador de cache com TTL"""
    
    def __init__(self, ttl_hours: int = 1):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_hours * 3600
        
    def _generate_cache_key(self, **kwargs) -> str:
        """Gera uma chave única para o cache baseada nos parâmetros"""
        # Ordenar os parâmetros para garantir consistência
        sorted_params = sorted(kwargs.items())
        param_string = json.dumps(sorted_params, sort_keys=True)
        return hashlib.md5(param_string.encode()).hexdigest()
    
    def get(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Busca dados no cache"""
        cache_key = self._generate_cache_key(**kwargs)
        
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            current_time = time.time()
            
            # Verificar se o cache ainda é válido
            if current_time - cache_entry['timestamp'] < self.ttl_seconds:
                print(f"📦 Cache HIT para chave: {cache_key[:8]}...")
                return cache_entry['data']
            else:
                # Cache expirado, remover
                print(f"⏰ Cache EXPIRADO para chave: {cache_key[:8]}...")
                del self.cache[cache_key]
        
        print(f"❌ Cache MISS para chave: {cache_key[:8]}...")
        return None
    
    def set(self, data: Dict[str, Any], **kwargs) -> None:
        """Armazena dados no cache"""
        cache_key = self._generate_cache_key(**kwargs)
        current_time = time.time()
        
        self.cache[cache_key] = {
            'data': data,
            'timestamp': current_time,
            'created_at': datetime.fromtimestamp(current_time).isoformat()
        }
        
        print(f"💾 Cache SET para chave: {cache_key[:8]}...")
    
    def flush(self) -> Dict[str, Any]:
        """Remove todos os dados do cache e retorna estatísticas"""
        cache_size = len(self.cache)
        cache_keys = list(self.cache.keys())
        
        # Limpar cache
        self.cache.clear()
        
        stats = {
            'action': 'flush',
            'cache_size_before': cache_size,
            'cache_size_after': 0,
            'keys_removed': cache_keys,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"🧹 Cache FLUSHED - {cache_size} entradas removidas")
        return stats
    
    def flush_expired(self) -> Dict[str, Any]:
        """Remove apenas entradas expiradas do cache"""
        current_time = time.time()
        expired_keys = []
        
        for cache_key, cache_entry in list(self.cache.items()):
            if current_time - cache_entry['timestamp'] >= self.ttl_seconds:
                expired_keys.append(cache_key)
                del self.cache[cache_key]
        
        stats = {
            'action': 'flush_expired',
            'expired_entries': len(expired_keys),
            'remaining_entries': len(self.cache),
            'expired_keys': expired_keys,
            'timestamp': datetime.now().isoformat()
        }
        
        if expired_keys:
            print(f"🧹 Cache EXPIRED FLUSHED - {len(expired_keys)} entradas expiradas removidas")
        else:
            print(f"✅ Cache EXPIRED FLUSH - Nenhuma entrada expirada encontrada")
        
        return stats
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        current_time = time.time()
        total_entries = len(self.cache)
        expired_entries = 0
        valid_entries = 0
        
        for cache_entry in self.cache.values():
            if current_time - cache_entry['timestamp'] >= self.ttl_seconds:
                expired_entries += 1
            else:
                valid_entries += 1
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'ttl_hours': self.ttl_seconds / 3600,
            'cache_size_mb': self._estimate_memory_usage(),
            'timestamp': datetime.now().isoformat()
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estima o uso de memória do cache em MB"""
        try:
            cache_size = len(json.dumps(self.cache))
            return round(cache_size / (1024 * 1024), 2)
        except:
            return 0.0

# Instância global do cache
basic_data_cache = CacheManager(ttl_hours=1)

# Instâncias de cache para outros endpoints
daily_metrics_cache = CacheManager(ttl_hours=1)
orders_cache = CacheManager(ttl_hours=1)
detailed_data_cache = CacheManager(ttl_hours=4)

# Sistema para salvar último request
import os
import json
from datetime import datetime, timedelta

class LastRequestManager:
    """Gerenciador para salvar o último request de cada endpoint por cliente com persistência de 30 dias"""
    
    def __init__(self, storage_file: str = "last_requests.json"):
        self.storage_file = storage_file
        self.last_requests: Dict[str, Dict[str, Any]] = {}
        self.ttl_days = 30
        self._load_from_storage()
    
    def _generate_key(self, endpoint: str, table_name: str) -> str:
        """Gera uma chave única para endpoint + table_name"""
        return f"{endpoint}:{table_name}"
    
    def _load_from_storage(self) -> None:
        """Carrega dados do arquivo de storage"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Filtrar apenas entradas válidas (não expiradas)
                    current_time = datetime.now()
                    for key, value in data.items():
                        timestamp = datetime.fromisoformat(value['timestamp'])
                        if current_time - timestamp < timedelta(days=self.ttl_days):
                            self.last_requests[key] = value
                    print(f"📂 Carregados {len(self.last_requests)} últimos requests do storage")
        except Exception as e:
            print(f"⚠️ Erro ao carregar storage: {e}")
            self.last_requests = {}
    
    def _save_to_storage(self) -> None:
        """Salva dados no arquivo de storage"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.last_requests, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Erro ao salvar storage: {e}")
    
    def _cleanup_expired(self) -> None:
        """Remove entradas expiradas"""
        current_time = datetime.now()
        expired_keys = []
        
        for key, value in list(self.last_requests.items()):
            timestamp = datetime.fromisoformat(value['timestamp'])
            if current_time - timestamp >= timedelta(days=self.ttl_days):
                expired_keys.append(key)
                del self.last_requests[key]
        
        if expired_keys:
            print(f"🧹 Removidas {len(expired_keys)} entradas expiradas do last-request")
            self._save_to_storage()
    
    def save_last_request(self, endpoint: str, request_data: Dict[str, Any], user_email: str) -> None:
        """Salva o último request de um endpoint para um cliente específico"""
        table_name = request_data.get('table_name', 'unknown')
        key = self._generate_key(endpoint, table_name)
        
        self.last_requests[key] = {
            'request_data': request_data,
            'user_email': user_email,
            'timestamp': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        # Salvar no storage
        self._save_to_storage()
        
        # Limpar entradas expiradas periodicamente
        if len(self.last_requests) % 10 == 0:  # A cada 10 saves
            self._cleanup_expired()
        
        print(f"💾 Último request salvo para {endpoint} - Cliente: {table_name} (TTL: {self.ttl_days} dias)")
    
    def get_last_request(self, endpoint: str, table_name: str) -> Optional[Dict[str, Any]]:
        """Busca o último request de um endpoint para um cliente específico"""
        key = self._generate_key(endpoint, table_name)
        request_data = self.last_requests.get(key)
        
        if request_data:
            # Verificar se não expirou
            timestamp = datetime.fromisoformat(request_data['timestamp'])
            if datetime.now() - timestamp < timedelta(days=self.ttl_days):
                return request_data
            else:
                # Remover se expirou
                del self.last_requests[key]
                self._save_to_storage()
                print(f"⏰ Request expirado para {endpoint} - Cliente: {table_name}")
        
        return None
    
    def get_all_last_requests(self, endpoint: str) -> Dict[str, Dict[str, Any]]:
        """Busca todos os últimos requests de um endpoint para todos os clientes"""
        result = {}
        current_time = datetime.now()
        
        for key, value in self.last_requests.items():
            if key.startswith(f"{endpoint}:"):
                # Verificar se não expirou
                timestamp = datetime.fromisoformat(value['timestamp'])
                if current_time - timestamp < timedelta(days=self.ttl_days):
                    table_name = key.split(":", 1)[1]
                    result[table_name] = value
                else:
                    # Remover se expirou
                    del self.last_requests[key]
        
        if result != self.last_requests:
            self._save_to_storage()
        
        return result
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do storage"""
        current_time = datetime.now()
        total_entries = len(self.last_requests)
        valid_entries = 0
        expired_entries = 0
        
        for value in self.last_requests.values():
            timestamp = datetime.fromisoformat(value['timestamp'])
            if current_time - timestamp < timedelta(days=self.ttl_days):
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'ttl_days': self.ttl_days,
            'storage_file': self.storage_file,
            'file_size_mb': round(os.path.getsize(self.storage_file) / (1024 * 1024), 2) if os.path.exists(self.storage_file) else 0
        }

# Instância global do gerenciador de último request
last_request_manager = LastRequestManager() 