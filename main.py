# Middleware
from fastapi import FastAPI, HTTPException, File, UploadFile, Body, Form
from fastapi.responses import Response
from pydantic import BaseModel, Field, create_model
from typing import List, Dict, Union, Optional


# Backend
from processor import EnrichRequestItem, process_data_api_concurrently_async
from a2wsgi import WSGIMiddleware
from sqlalchemy import create_engine, text

# Frontend
from pathlib import Path
from loguru import logger
import pandas as pd
import numpy as np
import io 
import os

# Dash
from dash_extensions.enrich import DashProxy
import pathlib
import dash_bootstrap_components as dbc
from loguru import logger
from component import user_interface
from callbacks import register_data_callbacks
import os


def create_app_dash():

    logger.info("setting up app_dash")

    # Define the absolute path to the assets folder


    # Define the absolute path to the assets folder reliably
    # Use pathlib to construct the absolute path if running locally
    if os.environ['APP_ENV'] == 'local':
        assets_path = pathlib.Path(__file__).parent.resolve() / "assets"
    else:
        # Default to runpod path if needed
        assets_path = "/workspace/mvp/assets"

    app_dash = DashProxy(
            requests_pathname_prefix="/dash/",
            external_stylesheets=[dbc.themes.DARKLY],
            assets_folder=assets_path # Provide the absolute path here

        )

    configure_dev_tools(app_dash, os.getenv("ENVIRONMENT", "DEV"))


    app_dash.layout = user_interface


    register_data_callbacks(app_dash)

    logger.info("app_dash is configured")
    return app_dash

def configure_dev_tools(app, env):
    """
    Enables Dash dev tools on the provided app instance with given options.
    """
    if env == "DEV":
        dev_tools_options = {
            "debug": True,
            "dev_tools_ui": True,
            "dev_tools_props_check": True,
            "dev_tools_serve_dev_bundles": True,
            "dev_tools_hot_reload": True,
        }
    else:
        dev_tools_options = {"debug": False}

    app.enable_dev_tools(**dev_tools_options)



# Define base paths regardless of environment
LOCAL_BASE = Path("/Users/intuitivecode/Code/mvp")
RUNPOD_BASE = Path("/workspace/mvp")

if 'APP_ENV' in os.environ and os.environ['APP_ENV'] == 'local':
    BASE_DIR = LOCAL_BASE
else:
    # Default to runpod if no env var is set, or set specific checks
    BASE_DIR = RUNPOD_BASE

OUTPUT_DIR = BASE_DIR / "data"

app = FastAPI()

dash_app_instance = create_app_dash()

app.mount("/dash/", WSGIMiddleware(dash_app_instance.server))
db_engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./.database.db"))


# Produced for user. Increased tokens used by a lot
class DefaultProductAttributes(BaseModel):
    # Rename 'sku' to 'identifier' or 'original_name' to be explicit
    id: int = Field(description="[INTERNAL] Stable integer ID for database operations.")    
    insight: str = Field(description="Actionable feedback or status regarding data quality.")    
    anomaly_flag: Optional[str] = Field(description="Notes if this row contains unusual data points or potential errors (e.g., 'Price listed seems unusually low' or 'Unrecognized size format').")
    quality_score: int = Field(description="An integer score (1-5) indicating the completeness and clarity of the product description data, where 5 is excellent.")


# Payload fields from user's custom field entries
class CustomField(BaseModel):
    name: str
    description: str

# Model for the overall configuration sent from Dash
class SchemaPayload(BaseModel):
    mode: str # 'defaults' or 'custom'
    fields: List[CustomField]


@app.post("/enrich-products", summary="Enrich a list of product items")
async def upload_and_enrich_csv_endpoint(file: UploadFile = File(...), schema_config_str: str = Form(...)):

    logger.info("Receiving post from Dash inside fastapi")

    try:
        schema_data = SchemaPayload.model_validate_json(schema_config_str)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON format for schema_config: {str(e)}")
    
    # --- LOGIC TO DETERMINE THE PYDANTIC MODEL DYNAMICALLY ---
    if schema_data.mode == 'defaults':
        output_schema = DefaultProductAttributes # Use your hardcoded default
    elif schema_data.mode == 'custom':
        fields_dict = {
            'id': (int, Field(description="[INTERNAL] Stable integer ID for database ops.")),
        }
        for field in schema_data.fields:
            # Dynamically add the user's field name and description
            fields_dict[field.name] = (Optional[str], Field(description=field.description))

        output_schema = create_model('DynamicProductAttributes', **fields_dict)
    else:
        raise HTTPException(status_code=400, detail="Invalid schema mode provided.")

    content = await file.read()
    try:
        df_original = pd.read_csv(io.StringIO(content.decode('utf-8')), engine='python', on_bad_lines='skip') 
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")

    if df_original.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty.")
    

    expected_fields = set(EnrichRequestItem.model_fields.keys())
    csv_columns = set(df_original.columns)
    valid_columns_to_keep = list(expected_fields.intersection(csv_columns))
    REQUIRED_FIELD = "product_name" 
    if REQUIRED_FIELD not in valid_columns_to_keep:
        raise HTTPException(status_code=400, detail=f"CSV must contain the required column: '{REQUIRED_FIELD}'.")
    df_filtered = df_original[valid_columns_to_keep]

    df_filtered = df_filtered.replace({np.nan: None}) 

    df_filtered['id'] = range(1, len(df_filtered) + 1)
    try:
        items_for_processing = [EnrichRequestItem(**row) for row in df_filtered.to_dict(orient='records')]
    except Exception as e:
         raise HTTPException(status_code=422, detail=f"Data validation error in CSV rows: {str(e)}")

    enriched_results = await process_data_api_concurrently_async(items_for_processing, output_schema)




    df_enriched = pd.DataFrame(enriched_results)

    df_original_and_enriched = pd.merge(df_filtered, df_enriched, left_on='id', right_on='id', how='left')

    logger.info(f"DEBUG: Processed {len(df_original_and_enriched)} items.") 

    # In case user had some "bad" rows, replace NaNs introduced by the LEFT MERGE w/ NONE
    df_original_and_enriched = df_original_and_enriched.replace({np.nan: None})


    # Write the DataFrame to the SQLite database
    df_original_and_enriched.to_sql(
        name="enrichment_results", 
        con=db_engine, 
        if_exists='replace',
        index=False
    )

    # --- For API functionality: Return the data ---
    return df_original_and_enriched.to_dict(orient='records')



@app.get("/download-results")
def download_results_csv():

    if db_engine is None:
        logger.error("Database engine not initialized.")
        return {"error": "Server configuration error."}
    
    df_final = pd.read_sql_table(
        con=db_engine,
        table_name="enrichment_results"
    )
    
    if df_final.empty:
        return {"error": "No data found in the database to download."}

    csv_string = df_final.to_csv(index=False, encoding='utf-8')

    # Some browsers need this to retain this specific file name
    headers = {
        "Content-Disposition": "attachment; filename=enrichment_results.csv"
    }

    return Response(
        content=csv_string,
        media_type="text/csv",
        headers=headers
    )


@app.put("/update-row")
def update_row_in_db(row_data: dict):
    # 'row_data' should contain the ID of the row and the changed column/value
    row_id = row_data.get('id') 

    # Add a check for the identifier key
    if not row_id:
        raise HTTPException(status_code=422, detail="Missing 'id' identifier key in request body.")

    engine = db_engine
    logger.info(f"hitting the update row endpoint! product name: {row_id}")
    try:
        with engine.connect() as connection:
            # Build the SET clause of the SQL query dynamically
            set_clauses = []
            parameters = {'id': row_id}            
            for column_name, value in row_data.items():
                if column_name != 'id':
                    set_clauses.append(f"{column_name} = :{column_name}")
                    parameters[column_name] = value
            
            # Construct the final query string
            query_sql = f"UPDATE enrichment_results SET {', '.join(set_clauses)} WHERE id = :id"

            # Execute the query
            connection.execute(text(query_sql), parameters)
            connection.commit()

        return {"status": "success", "message": f"Row {row_id} updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database update failed: {str(e)}")


@app.post("/resynthesize-batch")
async def resynthesize_batch_rows(rows_data: list[dict] = Body(...)):
    if not rows_data:
        raise HTTPException(status_code=422, detail="No rows provided for batch processing.")
    
    # 1. Convert incoming list of dicts to Pydantic models (EnrichRequestItem needs the 'id' field)
    try:
        items_for_processing = [EnrichRequestItem(**row) for row in rows_data]
    except Exception as e:
         raise HTTPException(status_code=422, detail=f"Data validation error in batch rows: {str(e)}")

    # 2. Await the asynchronous processing (this is the long-running step)
    enriched_results = await process_data_api_concurrently_async(items_for_processing)

    # 3. Process the results into DataFrames
    df_filtered = pd.DataFrame(rows_data) # Original data with IDs
    df_enriched = pd.DataFrame(enriched_results)

    # >>> FIX: Use the 'suffixes' parameter in merge <<<
    # We keep the enriched data (_y) which contains the new synthesis results
    # and drop the original data (_x) columns.
    df_updated_rows = pd.merge(
        df_filtered, 
        df_enriched, 
        on='id', 
        how='left', 
        suffixes=('_original', '_new') # Use clear suffixes first
    )

    # Drop old column, replace with new, then drop the suffix
    # We must explicitly drop the old columns that have the suffix
    for col in df_updated_rows.columns:
        if col.endswith('_original'):
            df_updated_rows = df_updated_rows.drop(columns=[col])
        if col.endswith('_new'):
            # And rename the new ones back to their original DB name (product_type)
            df_updated_rows = df_updated_rows.rename(columns={col: col[:-4]}) # Remove the '_new' suffix

    # 4. Merge back the original data with the newly synthesized insights using the stable 'id'
    df_updated_rows = df_updated_rows.replace({np.nan: None})

    # 5. Update the Database
    # This is slightly tricky, you need to merge these updated rows back into your main DB table.
    # The simplest method is a series of UPDATE commands for each row ID.
    engine = db_engine # Get your DB engine
    try:
        with engine.connect() as connection:
            for index, row_series in df_updated_rows.iterrows():
                # Convert the row Series to a dictionary for easier access
                row_data = row_series.to_dict()
                
                row_id = row_data.get('id')
                if not row_id:
                    logger.warning(f"Skipping row {index}: Missing ID.")
                    continue # Skip this row if ID is missing

                # Build the SQL UPDATE query dynamically for this specific row
                set_clauses = []
                parameters = {'id': row_id}            
                
                for column_name, value in row_data.items():
                    if column_name != 'id':
                        set_clauses.append(f"{column_name} = :{column_name}")
                        parameters[column_name] = value

                if set_clauses:
                    query_sql = text(f"UPDATE enrichment_results SET {', '.join(set_clauses)} WHERE id = :id")
                    # Execute the update for this specific row
                    connection.execute(query_sql, parameters)
                
            # >>> COMMIT THE CHANGES AFTER THE LOOP FINISHES <<<
            connection.commit()
            logger.info(f"Batch update committed successfully for {len(df_updated_rows)} rows.")

    except Exception as e:
        logger.error(f"Batch DB update failed: {e}")
        # Rollback the transaction in case of error
        # connection.rollback() 
        raise HTTPException(status_code=500, detail="Failed to update database with batch results.")

    # >>> Return statement must be outside the try/except block and use the final data <<<
    return df_updated_rows.to_dict(orient='records')


@app.get("/get-all-data-json")
def get_all_data_from_db():
    logger.info("Fetching all data from database for UI refresh.")
    try:
        df_all_data = pd.read_sql_table(
            con=db_engine,
            table_name="enrichment_results"
        )
        return df_all_data.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error fetching all data from DB: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve data for UI refresh.")