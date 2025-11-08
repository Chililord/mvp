from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Dict, Any # <-- Ensure Dict and Any are imported
import ollama
import asyncio
from loguru import logger


'''

If you need to terminate for a new gpu, run these in order to sync with git repo:
cp -r .ssh/* /root/.ssh/
chmod 600 /root/.ssh/*


curl -X POST "https://0dsh3n5qguhykz-8000.proxy.runpod.net/enrich_products" \
     -H "Content-Type: application/json" \
     --data @app-mvp/data/large_products_list.json

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
    """
    Makes an API call using the official Ollama SDK for reliable structured output, 
    validates the output, and ensures the identifier is included.
    """
    client = ollama.AsyncClient(host='http://localhost:11434')
    prompt = build_prompt_key_value(item)
    content = "" # Initialize content variable for error logging
    unique_id = item.sku if item.sku else item.product_name

    try:
        response = await client.chat(
            model='phi3',
            messages=[
                {'role': 'system', 'content': 'You are a ultra-concise data formatting AI. '
                'Your ONLY task is to generate a '
                'VALID and COMPLETE JSON object based on the user request and schema '
                'provided. Respond with nothing else. '
                'No conversational filler or extra words. '
                'No extraneous details or explanations'
                'Be direct and analytical. '
                'Each json field must be less than 10 tokens.'},
                {'role': 'user', 'content': prompt},
            ],
            options={
                'temperature': 0,
                'num_ctx': 500,
                'num_predict': 100
            },
            format=ProductAttributes.model_json_schema(), 
        )

        content = response['message']['content'].strip()

        # Validate the LLM output using Pydantic
        validated_product = ProductAttributes.model_validate_json(content)

        # Convert to dictionary immediately after validation
        validated_product_dict = validated_product.model_dump()

        # Ensure the identifier field matches the Pydantic output schema field name
        # We can trust this because Pydantic already validated that this field exists
        validated_product_dict['identifier'] = unique_id 
        
        return validated_product_dict

    except ValidationError as e:
        logger.error(f"Pydantic validation failed for item '{unique_id}'. Error: {e}")
        logger.error(f"Problematic content was: \n---\n{content}\n---\n")
        return None # Return None if validation fails

    except Exception as e:
        logger.error(f"Ollama API call failed for item '{unique_id}'. Error: {e}")
        logger.error(f"Problematic content was: \n---\n{content}\n---\n")
        return None # Return None for other API errors

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
