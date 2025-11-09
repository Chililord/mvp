from fastapi import FastAPI, HTTPException
from typing import List
from processor import EnrichRequestItem, process_data_api_concurrently_async


app = FastAPI(
    title="Product Attribute Enrichment API",
    description="An API service to enrich raw product data using a local LLM accelerator."
)

@app.post("/enrich_products_master", summary="Enrich a list of product items")
async def enrich_products_endpoint(items: List[EnrichRequestItem]):
    if not items:
        raise HTTPException(status_code=400, detail="Input list cannot be empty.")

    return await process_data_api_concurrently_async(items)
