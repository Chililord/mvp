from fastapi import FastAPI, HTTPException, Request
from typing import List
from src.processor import EnrichRequestItem, process_data_api_concurrently_async
from vllm import LLM, SamplingParams # pyright: ignore[reportMissingImports]
from contextlib import asynccontextmanager
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize the vLLM engine when the app starts up.
    """

    VLLM_MODEL_PATH = "/workspace/Phi-3-mini-4k-instruct"

    logger.info(f"Loading vLLM model: {VLLM_MODEL_PATH}...")
    
    # tensor_parallel_size can be adjusted based on GPU resources
    app.state.llm_engine = LLM(model=VLLM_MODEL_PATH, tensor_parallel_size=1) 
    logger.info("vLLM model loaded successfully.")
    
    yield
    
    app.state.llm_engine = None

app = FastAPI(lifespan=lifespan)

@app.post("/enrich_products", summary="Enrich a list of product items with an llm")
async def enrich_products_endpoint(items: List[EnrichRequestItem], request: Request):
    if not items:
        raise HTTPException(status_code=400, detail="Input list cannot be empty.")

    return await process_data_api_concurrently_async(items, request.app.state.llm_engine)
