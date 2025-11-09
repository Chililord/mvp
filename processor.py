from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import ollama
import asyncio
from loguru import logger
import os
'''

If you need to terminate for a new gpu, run these in order

*expose port 8000 in the runpod*

May need to reinstall in order to use the forced schema format parameter
curl -fsSL https://ollama.com/install.sh | sh
git config --global user.email "noahdouglasgarner@gmail.com"
git config --global user.name Noah Garner
cp -r .ssh/* /root/.ssh/
chmod 600 /root/.ssh/*
deactivate
cd mvp/
pip install -r requirements.txt

(Only need to run chmod 755 start.sh && ./start.sh if you build a new workspace)

Run ollama with:
pkill ollama
OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_MAX_VRAM=0 OLLAMA_NUM_PARALLEL=40 OLLAMA_KEEP_ALIVE=-1 OLLAMA_FLASH_ATTENTION=1 ollama serve

Run fastapi with (change port per machine):
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --env-file .env


# Curl the data to the llm, make sure to update host name and update port to match uvicorn's fastapi
curl -X POST "https://heuzrxi4l1brf4-8000.proxy.runpod.net/enrich_products" \
     -H "Content-Type: application/json" \
     --data @data/large_products_list.json

     
curl -X POST "http://localhost:8000/docs/enrich_products" \
     -H "Content-Type: application/json" \
     --data @data/large_products_list.json

'''

# NOTE: The Phi-3 model prefers to be helpful and descriptive. 
# When it can't find a brand name, its default behavior is to provide a helpful 
# explanation (like "No specific brand mentioned, hence empty string returned as 
# placeholder.") rather than strictly following your formatting rule of just returning 
# the simple string 'empty'
# something to note in case a bunch of data is not generated when expected for a column
# like brand name. This is VERY important to note

# INCREASES BOTH INPUT + OUTPUT, FED TO PROMPT + RETURNED TO USER
class ProductAttributes(BaseModel):
    # Rename 'sku' to 'identifier' or 'original_name' to be explicit
    identifier: str = Field(description="The unique identifier from the input (usually the product name or SKU).")
    product_type: str = Field(description="The general category of the product.")
    brand: Optional[str] = Field(description="The brand name.")
    size_quantity: Optional[str] = Field(alias="size quantity", description="A single, concise string for size/quantity. Format: '100g', '12 pack', 'Small', '1 box', etc. DO NOT use sentences or extra explanations. Keep it under 5 words.")
    price: Optional[float] = Field(description="The numeric value of the product's price, or null if not available.")
    currency: Optional[str] = Field(description="The three-letter ISO 4217 currency code (e.g., USD, EUR), or null if not available.")
    availability: Optional[str] = Field(description="The product's availability status (e.g., in stock, out of stock, preorder), or null if not available.")




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

    # 2. Embed the schema into your System Prompt
    system_prompt_content = (
        'You are a ultra-concise data formatting AI. '
        'Your ONLY task is to generate a VALID and COMPLETE JSON object '
        'based on the user request and schema provided. Use only the exact keys from the schema. '
        'No conversational filler or extra words. '
        'The "price" field must be a raw number (float/integer format only), with no currency symbols, commas, or words like "USD".'
        'Ensure "currency" field is a 3-letter code.'
        '\n\n### JSON Schema to follow:\n'
        # f'{json.dump(ProductAttributes.model_json_schema(), indent=2)}'
    )

    try:

        if 'APP_ENV' in os.environ and os.environ['APP_ENV'] == 'local':
            MODEL = "phi3"
        else:
            MODEL = "local-phi3-quantized"

        response = await client.chat(
            model=MODEL,
            messages=[
                {'role': 'system', 'content': system_prompt_content}, # Use the new prompt
                {'role': 'user', 'content': prompt},
            ],
            options={
                'temperature': 0,
                'num_ctx': 1000,
                'num_predict': 300
            },
            format=ProductAttributes.model_json_schema(), 
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


# Function to chunk a list into smaller batches
def chunk_list(data_list, batch_size):
    for i in range(0, len(data_list), batch_size):
        yield data_list[i:i + batch_size]

async def process_data_api_concurrently_async(all_items: List[EnrichRequestItem]):
    
    # Use a BATCH_SIZE that you know won't crash (e.g., 20 items for A5000)
    # THIS WILL CHANGE DEPENDING ON PYDANTIC SCHEMA OUTPUT LENGTH
    BATCH_SIZE = 30
    all_results = []
    
    for batch in chunk_list(all_items, BATCH_SIZE):
        # Process this small batch
        tasks = [call_llm_api_async(item) for item in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results.extend(results)
        
    
    return all_results