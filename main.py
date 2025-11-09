from fastapi import FastAPI, HTTPException
from typing import List
from processor import EnrichRequestItem, process_data_api_concurrently_async
import os
import json

app = FastAPI(
    title="Product Attribute Enrichment API",
    description="An API service to enrich raw product data using a cloud gpu enabled LLM accelerator."
)

# Ensure a directory for output files exists
OUTPUT_DIR = "/workspace/mvp/data"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

@app.post("/enrich_products", summary="Enrich a list of product items")
async def enrich_products_endpoint(items: List[EnrichRequestItem]):
    if not items:
        raise HTTPException(status_code=400, detail="Input list cannot be empty.")

    # This might take some time
    enriched_results = await process_data_api_concurrently_async(items)


    output_filename = f"enriched_products_list.json"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    with open(output_path, 'w') as f:
        # Use json.dump to write the list of dictionaries to the file
        json.dump(enriched_results, f, indent=4)
        
    # Instead of returning the data, return a success message and the filename
    return {
        "status": "Processing complete",
        "message": f"Enriched data saved successfully to {output_filename}",
        "file_path": output_path,
        "items_processed": len(enriched_results)
    }
