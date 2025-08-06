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