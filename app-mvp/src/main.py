from fastapi import FastAPI, HTTPException
from typing import List
from src.processor import EnrichRequestItem, process_data_api_concurrently_async
from vllm import LLM, SamplingParams # pyright: ignore[reportMissingImports]
from contextlib import asynccontextmanager
from loguru import logger


# Considerations when scaling  + performance improvement + llm quality improvements
# tensor_parallel_size=1 can be increased when you add more gpu
# max_tokens Limit: Your max_tokens=100 might be very restrictive depending on how much 
# "enrichment" you expect the LLM to provide. Make sure this is sufficient for your 
# e-commerce data needs (e.g., generating descriptions, categorizing, etc.).

VLLM_MODEL_PATH = "microsoft/Phi-3-mini-4k-instruct"

llm_engine: None

VLLM_SAMPLING_PARAMS = SamplingParams(
    temperature=0, 
    max_tokens=100,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize the vLLM engine when the app starts up.
    """
    global llm_engine
    logger.info(f"Loading vLLM model: {VLLM_MODEL_PATH}...")
    
    # tensor_parallel_size can be adjusted based on GPU resources
    llm_engine = LLM(model=VLLM_MODEL_PATH, tensor_parallel_size=1) 
    logger.info("vLLM model loaded successfully.")
    
    yield
    
    llm_engine = None

app = FastAPI(lifespan=lifespan)

@app.post("/enrich_products", summary="Enrich a list of product items with an llm")
async def enrich_products_endpoint(items: List[EnrichRequestItem]):
    if not items:
        raise HTTPException(status_code=400, detail="Input list cannot be empty.")

    return await process_data_api_concurrently_async(items)
