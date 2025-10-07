import sys
import os
import logging
import uvicorn
import json
import glob
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..api import routes
from rag_app.private_config import private_settings
from rag_app.core.implementations.query_engine.query_engine import QueryEngine
from rag_app.core.implementations.reranker.reranker import ResultReRanker
from rag_app.initialization import initialize_rag_components
from rag_app.core.implementations.query_optimizer.query_optimizer import QueryOptimizer
from .logger import setup_logging
from .core.middleware.context import RequestContextMiddleware
from fastapi.staticfiles import StaticFiles

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create FastAPI app
app = FastAPI(title=private_settings.APP_NAME, version=private_settings.APP_VERSION)

# First, add the RequestContextMiddleware
app.add_middleware(RequestContextMiddleware)

# Setup logging before any other operations
setup_logging()

# Get logger for this module
logger = logging.getLogger(__name__)

# Then add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=private_settings.cors_origins,
    allow_credentials=private_settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=private_settings.CORS_ALLOW_METHODS,
    allow_headers=private_settings.CORS_ALLOW_HEADERS,
    max_age=private_settings.CORS_MAX_AGE,
    expose_headers=["*"],
)

# Include the API router
app.include_router(routes.router)

def merge_configs(base_config: dict, new_config: dict) -> dict:
    merged_config = base_config.copy()
    for key, value in new_config.items():
        if key in merged_config:
            if isinstance(merged_config[key], dict) and isinstance(value, dict):
                merged_config[key] = merge_configs(merged_config[key], value)
            elif isinstance(merged_config[key], (list, set)) and isinstance(value, (list, set)):
                merged_config[key] = list(set(merged_config[key]).union(value))
            else:
                merged_config[key] = value
        else:
            merged_config[key] = value
    return merged_config

async def init_query_engine():
    try:
        # 1. Read all config files in the CONFIGS_FOLDER
        config_files = glob.glob(os.path.join(private_settings.CONFIGS_FOLDER, "config_*.json"))
        
        # Filter out the template file from regular config files
        regular_config_files = [f for f in config_files if not f.endswith('template.json')]
        template_file = os.path.join(private_settings.CONFIGS_FOLDER, "config_template.json")

        if regular_config_files:
            # Use the latest non-template config file
            latest_config_file = max(regular_config_files)
            logger.info(f"Using latest configuration file: {latest_config_file}")
        elif os.path.exists(template_file):
            # Fall back to template if no other config files exist
            latest_config_file = template_file
            logger.info(f"No regular config files found. Using template configuration: {template_file}")
        else:
            logger.warning("No configuration files found. Using default configuration.")
            return

        # 2. Load the JSON from the latest config file
        with open(latest_config_file, 'r') as f:
            config_data = json.load(f)

        # 3. Merge with the private config
        merged_config = merge_configs(private_settings.dict(), config_data)
        logger.info(f"Using merged config file: {merged_config}")

        # 4. Call initialize_rag_components with the merged config
        domain_manager, chat_model, embedding_model, chunk_strategy = initialize_rag_components(merged_config)

        # 5. Initialize the Query Engine
        query_engine = QueryEngine(
            domain_manager=domain_manager,
            vector_stores=domain_manager.vector_stores,
            embedding_model=embedding_model,
            chat_model=chat_model,
            chunk_strategy=chunk_strategy,
            query_optimizer=QueryOptimizer(chat_model=chat_model) if merged_config['query_engine'].get('USE_QUERY_OPTIMIZER', True) else None,
            result_re_ranker=ResultReRanker() if merged_config['query_engine'].get('USE_RESULT_RE_RANKER', True) else None
        )

        # Update the global query_engine in the routes module
        routes.query_engine = query_engine
        routes.domain_manager = domain_manager

        logger.info("Query engine initialized successfully on startup")
    except Exception as e:
        logger.error(f"Error initializing query engine on startup: {str(e)}")
        raise

# Add startup event to initialize query engine
@app.on_event("startup")
async def startup_event():
    await init_query_engine()

app.mount("/", StaticFiles(directory=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../public")), html=True), name="static")
