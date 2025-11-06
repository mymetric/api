#!/usr/bin/env python3
"""
Script para testar carga da API e medir performance
"""

import asyncio
import aiohttp
import time
import json
from typing import List, Dict
import statistics

# Configurações do teste
API_BASE_URL = "http://localhost:8000"
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhY2NvdW50c0BteW1ldHJpYy5jb20uYnIiLCJleHAiOjE3NjE2NTg5OTUsInR5cGUiOiJhY2Nlc3MifQ.Psi1YDSVGuvqvXgwoSwywK112q7aYdv58Sug_7z-q6Q"

# Payloads de teste
BASIC_DATA_PAYLOAD = {
    "start_date": "2025-10-01",
    "end_date": "2025-10-23",
    "table_name": "coffeemais",
    "attribution_model": "Último Clique Não Direto"
}

DETAILED_DATA_PAYLOAD = {
    "start_date": "2025-10-01",
    "end_date": "2025-10-23",
    "table_name": "coffeemais",
    "attribution_model": "Último Clique Não Direto",
    "limit": 1000,
    "offset": 0,
    "order_by": "Pedidos"
}

async def make_request(session: aiohttp.ClientSession, endpoint: str, payload: Dict) -> Dict:
    """Faz uma requisição para a API"""
    headers = {
        'Authorization': f'Bearer {TEST_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    start_time = time.time()
    try:
        async with session.post(f"{API_BASE_URL}{endpoint}", 
                              json=payload, 
                              headers=headers) as response:
            response_data = await response.json()
            end_time = time.time()
            
            return {
                'status': response.status,
                'response_time': end_time - start_time,
                'success': response.status == 200,
                'data_size': len(str(response_data)) if response_data else 0
            }
    except Exception as e:
        end_time = time.time()
        return {
            'status': 0,
            'response_time': end_time - start_time,
            'success': False,
            'error': str(e)
        }

async def run_load_test(endpoint: str, payload: Dict, concurrent_requests: int, total_requests: int):
    """Executa teste de carga"""
    print(f"\n🧪 Testando {endpoint}")
    print(f"📊 {concurrent_requests} requisições simultâneas, {total_requests} total")
    
    connector = aiohttp.TCPConnector(limit=concurrent_requests * 2)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Criar lista de tarefas
        tasks = []
        for i in range(total_requests):
            task = make_request(session, endpoint, payload)
            tasks.append(task)
        
        # Executar todas as requisições
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Processar resultados
        successful_requests = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_requests = [r for r in results if isinstance(r, dict) and not r.get('success')]
        exceptions = [r for r in results if not isinstance(r, dict)]
        
        # Calcular métricas
        total_time = end_time - start_time
        response_times = [r['response_time'] for r in successful_requests]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max_response_time
        else:
            avg_response_time = median_response_time = min_response_time = max_response_time = p95_response_time = 0
        
        # Exibir resultados
        print(f"✅ Requisições bem-sucedidas: {len(successful_requests)}/{total_requests}")
        print(f"❌ Requisições falharam: {len(failed_requests)}")
        print(f"💥 Exceções: {len(exceptions)}")
        print(f"⏱️  Tempo total: {total_time:.2f}s")
        print(f"📈 Requisições/segundo: {total_requests/total_time:.2f}")
        print(f"📊 Tempo de resposta:")
        print(f"   • Média: {avg_response_time:.3f}s")
        print(f"   • Mediana: {median_response_time:.3f}s")
        print(f"   • Mínimo: {min_response_time:.3f}s")
        print(f"   • Máximo: {max_response_time:.3f}s")
        print(f"   • P95: {p95_response_time:.3f}s")
        
        # Mostrar alguns erros se houver
        if failed_requests:
            print(f"\n❌ Primeiros erros:")
            for i, error in enumerate(failed_requests[:3]):
                print(f"   {i+1}. Status: {error.get('status', 'N/A')}, Tempo: {error.get('response_time', 0):.3f}s")
                if 'error' in error:
                    print(f"      Erro: {error['error']}")

async def main():
    """Função principal do teste"""
    print("🚀 Iniciando teste de carga da API")
    print(f"🎯 URL base: {API_BASE_URL}")
    
    # Teste 1: Basic Data - 10 requisições simultâneas
    await run_load_test("/metrics/basic-data", BASIC_DATA_PAYLOAD, 10, 50)
    
    # Teste 2: Detailed Data - 5 requisições simultâneas (mais pesado)
    await run_load_test("/metrics/detailed-data", DETAILED_DATA_PAYLOAD, 5, 25)
    
    # Teste 3: Stress test - 20 requisições simultâneas
    await run_load_test("/metrics/basic-data", BASIC_DATA_PAYLOAD, 20, 100)
    
    print("\n✅ Teste de carga concluído!")

if __name__ == "__main__":
    asyncio.run(main())
