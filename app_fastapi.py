from fastapi import FastAPI, HTTPException, File, UploadFile
from typing import List
from processor import EnrichRequestItem, process_data_api_concurrently_async
import os
from pathlib import Path
import json
from loguru import logger
import pandas as pd
import numpy as np
import io 

app = FastAPI(
    title="Product Attribute Enrichment API",
    description="An API service to enrich raw product data using a cloud gpu enabled LLM accelerator."
)


# Define base paths regardless of environment
LOCAL_BASE = Path("/Users/intuitivecode/Code/mvp")
RUNPOD_BASE = Path("/workspace/mvp")

if 'APP_ENV' in os.environ and os.environ['APP_ENV'] == 'local':
    BASE_DIR = LOCAL_BASE
else:
    # Default to runpod if no env var is set, or set specific checks
    BASE_DIR = RUNPOD_BASE

OUTPUT_DIR = BASE_DIR / "data"


@app.post("/enrich_products", summary="Enrich a list of product items")
async def upload_and_enrich_csv_endpoint(file: UploadFile = File(...)):

    logger.info("Receiving post from Dash inside fastapi")

    content = await file.read()
    # Handle inconsistent rows, we don't know how bad user input will be
    try:
        # Set 'sep=None' and 'engine='python'' to let pandas autodetect delimiters 
        # and handle inconsistent rows more flexibly.
        df_original = pd.read_csv(io.StringIO(content.decode('utf-8')), engine='python', on_bad_lines='skip') 
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")

    if df_original.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty.")
    
    # 1. Dynamically get expected field names from your Pydantic model
    expected_fields = set(EnrichRequestItem.model_fields.keys())
    
    # 2. Identify which expected fields are actually in the user's CSV
    csv_columns = set(df_original.columns)
    valid_columns_to_keep = list(expected_fields.intersection(csv_columns))
    
    # 3. Ensure the required field is present
    REQUIRED_FIELD = "product_name" 
    if REQUIRED_FIELD not in valid_columns_to_keep:
        raise HTTPException(status_code=400, detail=f"CSV must contain the required column: '{REQUIRED_FIELD}'.")

    # 4. Select only the relevant columns from the DataFrame
    df_filtered = df_original[valid_columns_to_keep]

    # Replace all NaN (Not a Number) float values with None (Python's null)
    # Pydantic understands None for Optional fields. It does not understand NaN
    df_filtered = df_filtered.replace({np.nan: None}) 

    # 5. Convert rows to Pydantic models (Pandas .to_dict(orient='records') works well here)
    # Pydantic will use the Optional status to handle any columns missing from this specific CSV
    try:
        items_for_processing = [EnrichRequestItem(**row) for row in df_filtered.to_dict(orient='records')]
    except Exception as e:
         raise HTTPException(status_code=422, detail=f"Data validation error in CSV rows: {str(e)}")

    # ... (rest of your processing logic) ...
    enriched_results = await process_data_api_concurrently_async(items_for_processing)

    df_enriched = pd.DataFrame(enriched_results)

    df_original_and_enriched = pd.merge(df_original, df_enriched, left_on='product_name', right_on='identifier', how='left')

    logger.info(f"DEBUG: Processed {len(df_original_and_enriched)} items.") 

    # In case user had some "bad" rows, replace NaNs introduced by the LEFT MERGE w/ NONE
    df_original_and_enriched = df_original_and_enriched.replace({np.nan: None})
    
    # --- For API functionality: Return the data ---
    return df_original_and_enriched.to_dict(orient='records') # <-- Correct way
