from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Dict, Any
import ollama
import asyncio
from loguru import logger
import json

'''

If you need to terminate for a new gpu, run these in order to sync with git repo:

git config --global user.email "noahdouglasgarner@gmail.com"
git config --global user.name Noah Garner
cp -r .ssh/* /root/.ssh/
chmod 600 /root/.ssh/*
deactivate
apt-get update
apt-get install -y --reinstall python3-pip python3-venv python3-setuptools
pip install -r requirements.txt
*expose port 8000 in the runpod*


Run ollama with:
pkill ollama
OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_MAX_VRAM=0 OLLAMA_NUM_PARALLEL=24 OLLAMA_KEEP_ALIVE=-1 OLLAMA_FLASH_ATTENTION=1 ollama serve

Run fastapi with (change port per machine):
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --env-file .env


# Curl the data to the llm, make sure to update host name and update port to match uvicorn's fastapi
curl -X POST "https://zfvzra5n6ryvu0-8000.proxy.runpod.net/enrich_products" \
     -H "Content-Type: application/json" \
     --data @data/medium_products_list.json

'''

# NOTE: The Phi-3 model prefers to be helpful and descriptive. 
# When it can't find a brand name, its default behavior is to provide a helpful 
# explanation (like "No specific brand mentioned, hence empty string returned as 
# placeholder.") rather than strictly following your formatting rule of just returning 
# the simple string 'empty'
# something to note in case a bunch of data is not generated when expected for a column
# like brand name. This is VERY important to note
class ProductAttributes(BaseModel):
    # Rename 'sku' to 'identifier' or 'original_name' to be explicit
    identifier: str = Field(description="The unique identifier from the input (usually the product name or SKU).")
    product_type: str = Field(description="The general category of the product.")
    brand: str = Field(description="The brand name.")
    size_quantity: str = Field(description="A single, concise string for size/quantity. Format: '100g', '12 pack', 'Small', '1 box', etc. DO NOT use sentences or extra explanations. Keep it under 5 words.")


# Define the *Input* schema for the API endpoint (Standardized keys)
class EnrichRequestItem(BaseModel):
    product_name: str = Field(..., description="[REQUIRED] The primary name of the product.")
    product_description: Optional[str] = Field(None, description="[OPTIONAL] Additional descriptive text for improved accuracy.")
    manufacturer: Optional[str] = Field(None, description="[OPTIONAL] The legal manufacturer of the product.")
    sku: Optional[str] = Field(None, description="[OPTIONAL] Your internal Stock Keeping Unit (SKU) or MPN.")
    target_market: Optional[str] = Field(None, description="[OPTIONAL] The intended market audience (e.g., B2B, consumer).")
    user_defined_tags: Optional[str] = Field(None, description="[OPTIONAL] Existing tags or category hints from your system.")
    # Used as join key later
    sku: Optional[str] = Field(None, description="[OPTIONAL] Your internal Stock Keeping Unit (SKU) or MPN.") 

    # Add a Pydantic Config class to provide a better example to Swagger UI
    class Config:
        json_schema_extra = {
            "example": {
                "product_name": "Example product name only",
                # The optional fields are simply omitted from this example
            }
        }


# Build 'key: value' prompt format for the llm from pydantic input schema
# This gives the llm entire row context
# Greatly improves pydantic output schema results over just reading 'product_name'
def build_prompt_key_value(item: EnrichRequestItem):
    prompt_text = "Analyze the following product data:\n"
    
    # Use item.dict(exclude_none=True) to dynamically include only provided fields
    for key, value in item.model_dump(exclude_none=True).items():
        if str(value).strip(): 
            prompt_text += f"   '{key}': '{value}'\n"

    prompt_text += "Return a JSON object describing its attributes based on your schema.\n"
    return prompt_text


async def call_llm_api_async(item: EnrichRequestItem) -> Optional[Dict[str, Any]]:
    # ... (imports needed: from pydantic import BaseModel, Field, etc.)
    client = ollama.AsyncClient(host='http://localhost:11434')
    prompt = build_prompt_key_value(item)
    content = ""
    unique_id = item.sku if item.sku else item.product_name

    # 1. Generate the JSON Schema string
    product_schema_dict = ProductAttributes.model_json_schema()

    # Convert the dictionary to a formatted string representation
    product_schema_string = json.dumps(product_schema_dict, indent=2)


    # 2. Embed the schema into your System Prompt
    system_prompt_content = (
        'You are a ultra-concise data formatting AI. '
        'Your ONLY task is to generate a VALID and COMPLETE JSON object '
        'based on the user request and schema provided. Use only the exact keys from the schema. '
        'No conversational filler or extra words. '
        '\n\n### JSON Schema to follow:\n' + product_schema_string # This concatenation is now valid
    )

    try:
        response = await client.chat(
            model='local-phi3-quantized', # FIX 2: Use the registered name
            messages=[
                {'role': 'system', 'content': system_prompt_content}, # Use the new prompt
                {'role': 'user', 'content': prompt},
            ],
            options={
                'temperature': 0,
                'num_ctx': 500,
                'num_predict': 100
            },
            format="json", # FIX 3: Use the literal string "json"
        )
        
        # FIX 4: Access content safely (adjust if SDK structure is different)
        content = response['message']['content'].strip() 

        # Validate the LLM output using Pydantic
        validated_product = ProductAttributes.model_validate_json(content)
        validated_product_dict = validated_product.model_dump()

        validated_product_dict['identifier'] = unique_id 
        
        return validated_product_dict
    
    except Exception as e:
        # Log the problematic content if validation fails for debugging Pydantic errors
        print(f"Ollama API call failed for item '{unique_id}'. Error: {e}")
        print(f"Problematic content was: ---{content}---")
        return None # Or raise the exception if you prefer


# you need to add the type hints (List, Dict, Any) and import them from the typing module.
async def process_data_api_concurrently_async(data_list: list[EnrichRequestItem]) -> List[Dict[str, Any]]:

    tasks = [call_llm_api_async(data) for data in data_list]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    results_dicts = []
    for result in results:
        if isinstance(result, dict): 
            results_dicts.append(result)
        elif isinstance(result, Exception):
             logger.info(f"An async task failed with error: {result}")
            
    return results_dicts
