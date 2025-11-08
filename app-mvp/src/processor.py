from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Dict, Any
import asyncio
from vllm import LLM, SamplingParams
from loguru import logger

'''




curl -X POST "https://rp74h11fuubrot-8000.proxy.runpod.net/" \
     -H "Content-Type: application/json" \
     --data @data/large_products_list.json





'''



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


def build_user_prompt_key_value(item: EnrichRequestItem):
    prompt_text = "Analyze the following product data:\n"
    
    # Use item.dict(exclude_none=True) to dynamically include only provided fields
    for key, value in item.model_dump(exclude_none=True).items():
        if str(value).strip(): 
            prompt_text += f"   '{key}': '{value}'\n"

    prompt_text += "Return a JSON object describing its attributes based on your schema.\n"
    return prompt_text


async def call_llm_api_async(item: EnrichRequestItem, llm_engine: LLM) -> Optional[Dict[str, Any]]:
    """
    Makes an API call using the official Ollama SDK for reliable structured output, 
    validates the output, and ensures the identifier is included.
    """
    user_prompt = build_user_prompt_key_value(item)
    unique_id = item.sku if item.sku else item.product_name
    content = "" # Initialize content variable for error logging

    system_prompt = (
        'You are a ultra-concise data formatting AI. Your ONLY task is to generate a '
        'VALID and COMPLETE JSON object based on the user request and schema provided. '
        'Respond with nothing else. No conversational filler or extra words. '
        'The required JSON schema is provided below. '
        f'Schema: {ProductAttributes.model_json_schema()}'
    )
    # This is a much cleaner approach... agreed
    prompt_template = f"<|system|>{system_prompt}<|end|><|user|>{user_prompt}<|end|><|assistant|>"

    try:
        # vLLM generate is a SYNCHRONOUS call but it is extremely fast because it runs on the GPU.
        # When used with asyncio.gather() (which you already do), it efficiently batches requests.
        
        # We pass a list of prompts (even if just one) to the engine
        outputs = llm_engine.generate(
            prompts=[prompt_template], 
            sampling_params=SamplingParams(
                            temperature=0, 
                            max_tokens=100,
                        )
        )

        # Extract the generated text content
        # There should only be one output as we passed one prompt
        content = outputs[0].outputs[0].text.strip()

        # Validate the LLM output using Pydantic
        validated_product = ProductAttributes.model_validate_json(content)

        # ... (rest of your validation logic is the same) ...
        validated_product_dict = validated_product.model_dump()
        validated_product_dict['identifier'] = unique_id 
        
        return validated_product_dict


    except ValidationError as e:
        logger.error(f"Pydantic validation failed for item '{unique_id}'. Error: {e}")
        logger.error(f"Problematic content was: \n---\n{content}\n---\n")
        return None # Return None if validation fails

    except Exception as e:
        logger.error(f"vLLM engine processing failed for item '{unique_id}'. Error: {e}")
        logger.error(f"Problematic content was: \n---\n{content}\n---\n")
        return None # Return None for other API errors

# you need to add the type hints (List, Dict, Any) and import them from the typing module.
async def process_data_api_concurrently_async(data_list: list[EnrichRequestItem], llm_engine: LLM) -> List[Dict[str, Any]]:

    tasks = [call_llm_api_async(data, llm_engine) for data in data_list]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    results_dicts = []
    for result in results:
        if isinstance(result, dict): 
            results_dicts.append(result)
        elif isinstance(result, Exception):
             logger.info(f"An async task failed with error: {result}")

    return results_dicts
