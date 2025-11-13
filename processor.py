from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import ollama
import asyncio
from loguru import logger
import os
'''
CICD is push to docker, wait for build, terminate pod and spin up for latest image

Run ollama:
    OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_MAX_VRAM=0 OLLAMA_NUM_PARALLEL=40 OLLAMA_KEEP_ALIVE=-1 OLLAMA_FLASH_ATTENTION=1 ollama serve

Run fastapi + dash runpod:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload --env-file .env

Run fastapi local + dash:
    python -m uvicorn main:app --host localhost --port 8000 --reload --env-file .env


'''



# Received from user. Only product_name is required
class EnrichRequestItem(BaseModel):
    id: int = Field(description="[INTERNAL] Stable integer ID for database operations.")
    product_name: str = Field(..., description="[REQUIRED] The primary name of the product.")
    product_description: Optional[str] = Field(None, description="[OPTIONAL] Additional descriptive text for improved accuracy.")
    # manufacturer: Optional[str] = Field(None, description="[OPTIONAL] The legal manufacturer of the product.")
    # sku: Optional[str] = Field(None, description="[OPTIONAL] Your internal Stock Keeping Unit (SKU) or MPN.")
    # target_market: Optional[str] = Field(None, description="[OPTIONAL] The intended market audience (e.g., B2B, consumer).")
    # user_defined_tags: Optional[str] = Field(None, description="[OPTIONAL] Existing tags or category hints from your system.")



def build_prompt_key_value(item: EnrichRequestItem):
    prompt_text = "Analyze the following product data:\n"

    # Use item.dict(exclude_none=True) to dynamically include only provided fields
    for key, value in item.model_dump(exclude_none=True).items():
        if str(value).strip(): 
            prompt_text += f"   '{key}': '{value}'\n"

    prompt_text += "Return a JSON object describing its attributes based on your schema.\n"
    return prompt_text


async def call_llm_api_async(item: EnrichRequestItem, output_schema) -> Optional[Dict[str, Any]]:
    # ... (imports needed: from pydantic import BaseModel, Field, etc.)
    client = ollama.AsyncClient(host='http://localhost:11434')
    prompt = build_prompt_key_value(item)
    content = ""

    # 2. Embed the schema into your System Prompt
    system_prompt_content = (
        'You are a ultra-concise data formatting AI.'
        'Your ONLY task is to generate a VALID and COMPLETE JSON object'
        'based on the user request and schema provided. Use only the exact keys from the schema.'
        'No conversational filler or extra words.'
        'The "price" field must be a raw number (float/integer format only), with no currency symbols, commas, or words like "USD".'
        'The insight field must be under 15 words and provide only one key observation'
        'Always use short, direct language'
        'Ensure "currency" field is a 3-letter code.'
        '\n\n### JSON Schema to follow:\n'
        f'{output_schema.model_json_schema()}'
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
            format=output_schema.model_json_schema(), 
        )
  
        # FIX 4: Access content safely (adjust if SDK structure is different)
        content = response['message']['content'].strip() 

        # Validate the LLM output using Pydantic
        validated_product = output_schema.model_validate_json(content)
        validated_product_dict = validated_product.model_dump()

        
        return validated_product_dict
    
    except Exception as e:
        # Log the problematic content if validation fails for debugging Pydantic errors
        print(f"Ollama API call failed for item '{validated_product_dict['id']}'. Error: {e}")
        print(f"Problematic content was: ---{content}---")
        return None # Or raise the exception if you prefer


# Function to chunk a list into smaller batches
def chunk_list(data_list, batch_size):
    for i in range(0, len(data_list), batch_size):
        yield data_list[i:i + batch_size]

async def process_data_api_concurrently_async(all_items: List[EnrichRequestItem], output_schema):
    
    # Use a BATCH_SIZE that you know won't crash (e.g., 20 items for A5000)
    # THIS WILL CHANGE DEPENDING ON PYDANTIC SCHEMA OUTPUT LENGTH
    BATCH_SIZE = 30
    all_results = []
    
    for batch in chunk_list(all_items, BATCH_SIZE):
        # Process this small batch
        tasks = [call_llm_api_async(item, output_schema) for item in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results.extend(results)
        
    return all_results