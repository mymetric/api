"""
Custom method for Havaianas client to access havaianas_item_scoring table
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from google.cloud import bigquery
from datetime import datetime, timedelta
import os

from utils import verify_token, TokenData, get_bigquery_client
from cache_manager import basic_data_cache

# Router for Havaianas custom methods
havaianas_router = APIRouter(prefix="/havaianas", tags=["havaianas"])

# Pydantic models for Havaianas item scoring
class HavaianasItemScoringRequest(BaseModel):
    table_name: str

class HavaianasItemScoringRow(BaseModel):
    event_date: Optional[str] = None
    item_id: Optional[str] = None
    item_name: Optional[str] = None
    elegible: Optional[int] = None
    item_views: Optional[int] = None
    size_score: Optional[float] = None
    promo_label: Optional[float] = None
    transactions: Optional[int] = None
    purchase_revenue: Optional[float] = None

class HavaianasItemScoringResponse(BaseModel):
    data: List[HavaianasItemScoringRow]
    total_rows: int
    summary: Dict[str, Any]
    cache_info: Optional[Dict[str, Any]] = None

@havaianas_router.post("/items-scoring", response_model=HavaianasItemScoringResponse)
async def havaianas_items_scoring(
    request: HavaianasItemScoringRequest,
    token: TokenData = Depends(verify_token)
):
    """
    Custom method for Havaianas client to access havaianas_item_scoring table
    """
    try:
        client = get_bigquery_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro de conexão com o banco de dados"
            )

        # Buscar informações do usuário para controle de acesso
        user_query = f"""
        SELECT tablename, access_control
        FROM `mymetric-hub-shopify.dbt_config.users`
        WHERE email = @email
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", token.email),
            ]
        )
        
        user_result = client.query(user_query, job_config=job_config)
        user_data = list(user_result.result())
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user_tablename = user_data[0].tablename
        access_control = user_data[0].access_control
        
        # Determinar qual tabela usar baseado no perfil do usuário
        if user_tablename == 'all':
            # Usuário tem acesso a todas as tabelas
            tablename = request.table_name
            print(f"🔓 Usuário com acesso total usando tabela: {tablename}")
        else:
            # Usuário tem acesso limitado a uma tabela específica
            if request.table_name != user_tablename:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuário só tem acesso à tabela '{user_tablename}', não pode acessar '{request.table_name}'"
                )
            tablename = user_tablename
            print(f"🔒 Usuário com acesso limitado usando tabela: {tablename}")

        # Build the query using the determined table name
        query_parts = [
            "SELECT",
            "  event_date,",
            "  item_id,",
            "  item_name,",
            "  elegible,",
            "  item_views,",
            "  size_score,",
            "  promo_label,",
            "  transactions,",
            "  purchase_revenue",
            f"FROM `bq-mktbr.dbt_aggregated.{tablename}_item_scoring`",
            "ORDER BY event_date DESC, item_id",
            "LIMIT 1000"
        ]

        query_parameters = []

        query = "\n".join(query_parts)

        # Execute the query
        job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())

        # Convert results to response format
        data = []
        for row in results:
            data.append(HavaianasItemScoringRow(
                event_date=str(row.event_date) if row.event_date else None,
                item_id=row.item_id,
                item_name=row.item_name,
                elegible=row.elegible,
                item_views=row.item_views,
                size_score=row.size_score,
                promo_label=row.promo_label,
                transactions=row.transactions,
                purchase_revenue=row.purchase_revenue
            ))

        # Calculate summary statistics
        summary = {
            "total_records": len(data),
            "total_views": sum(row.item_views or 0 for row in data),
            "total_transactions": sum(row.transactions or 0 for row in data),
            "total_revenue": sum(row.purchase_revenue or 0 for row in data),
            "avg_size_score": sum(row.size_score or 0 for row in data) / len(data) if data else 0,
            "avg_promo_label": sum(row.promo_label or 0 for row in data) / len(data) if data else 0,
            "elegible_items": sum(1 for row in data if row.elegible == 1),
            "non_elegible_items": sum(1 for row in data if row.elegible == 0)
        }

        return HavaianasItemScoringResponse(
            data=data,
            total_rows=len(data),
            summary=summary,
            cache_info=None
        )

    except Exception as e:
        print(f"Erro no método havaianas_items_scoring: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        ) 