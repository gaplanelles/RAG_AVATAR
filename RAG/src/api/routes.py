import os
import sys
import logging
import json
from fastapi import APIRouter, Depends, HTTPException, Body, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from datetime import datetime
import glob
import traceback
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple
import time
import shutil
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Interfaces
from rag_app.core.interfaces.query_engine_interface import QueryEngineInterface
from rag_app.core.interfaces.domain_manager_interface import DomainManagerInterface

# Implementations
from rag_app.core.implementations.conversation.conversation import Conversation
from rag_app.core.implementations.query_engine.query_engine import QueryEngine
from rag_app.core.implementations.query_optimizer.query_optimizer import QueryOptimizer
from rag_app.core.implementations.reranker.reranker import ResultReRanker
from rag_app.private_config import private_settings

# Config
from rag_app.initialization import initialize_rag_components

# Logs
logger = logging.getLogger(__name__)

# App
router = APIRouter()

# These will be updated in the /setup_RAG endpoint
query_engine: QueryEngine = None
domain_manager = None

def get_query_engine():
    if query_engine is None:
        raise HTTPException(status_code=500, detail="Query engine not initialized")
    return query_engine

def get_domain_manager():
    if domain_manager is None:
        raise HTTPException(status_code=500, detail="Domain manager not initialized")
    return domain_manager


# Add this new model
class AskRequest(BaseModel):
    message: str
    genModel: str
    conversation: List[Dict[str, str]] = []
    conversation_id: Optional[str] = None

# **New: InitRequest Model**
class InitRequest(BaseModel):
    genModel: str
    conversation_id: Optional[str] = None

# Add this global variable to store the single conversation
global_conversation: Optional[Conversation] = Conversation()

# Add this global variable to store the last response for the avatar
last_avatar_response: str = ""

@router.post("/clean_conversation")
async def clean_conversation():
    global global_conversation, last_avatar_response
    global_conversation = Conversation()
    last_avatar_response = ""
    return {"message": "Conversation has been cleaned."}

@router.get("/get_string")
async def get_string():
    """
    Get the last response string for the avatar to read.
    """
    global last_avatar_response
    return {"response": last_avatar_response}

@router.post("/setup_rag")
async def setup_rag(config_data: dict = Body(...)):
    global query_engine, domain_manager
    
    try:
        # Setup paths
        data_folder = Path(private_settings.DATA_FOLDER)
        chunks_folder = Path(private_settings.DATA_FOLDER).parent / 'chunks'

        # Clean chunks folder
        if chunks_folder.exists():
            # Remove all contents but keep the folder
            for item in chunks_folder.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            logger.info(f"Cleaned chunks directory: {chunks_folder}")
        else:
            # Create chunks folder if it doesn't exist
            chunks_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created chunks directory: {chunks_folder}")

        # Merge public settings with incoming config_data
        merged_config = merge_configs(private_settings.dict(), config_data)
        
        # Write the merged configuration to a file
        merged_config_path = os.path.join(private_settings.DOCS_FOLDER, "rag_setup_merged.json")
        with open(merged_config_path, "w") as merged_config_file:
            json.dump(merged_config, merged_config_file, indent=4)
        
        # Initialize components using the merged configuration
        domain_manager, chat_model, embedding_model, chunk_strategy = initialize_rag_components(merged_config)
        domain_manager.apply_chunking_strategy()
        
        # Initialize the query engine with the components
        query_engine = QueryEngine(
            domain_manager=domain_manager,
            vector_stores=domain_manager.vector_stores,
            embedding_model=embedding_model,
            chat_model=chat_model,
            chunk_strategy=chunk_strategy,
            query_optimizer=QueryOptimizer(chat_model=chat_model) if merged_config['query_engine'].get('USE_QUERY_OPTIMIZER', True) else None,
            result_re_ranker=ResultReRanker() if merged_config['query_engine'].get('USE_RESULT_RE_RANKER', True) else None
        )
        
        # Store the original config_data with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        config_filename = f"config_{timestamp}.json"
        config_path = os.path.join(private_settings.CONFIGS_FOLDER, config_filename)
        
        logger.info(f"Saving configuration to file: {config_path}") 
        try:
            with open(config_path, "w") as config_file:
                json.dump(config_data, config_file, indent=4)
            logger.info("Configuration saved successfully.")
        except IOError as e:
            logger.error(f"Error writing configuration file: {str(e)}")
        
        return {"message": "RAG system setup successfully"}
    except Exception as e:
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="An error occurred during setup")

@router.get("/setup_rag_template")
async def get_setup_rag_template():
    try:
        with open(os.path.join(private_settings.DOCS_FOLDER, "rag_setup_template.json"), "r") as template_file:
            template_data = json.load(template_file)
        return JSONResponse(content=template_data)
    except Exception as e:
        logger.error(f"Error loading setup RAG template: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while loading the template")

def has_consecutive_repetition(text: str, k: int = 10) -> bool:
    """
    Check if there is a consecutive repetition of at least k characters in the text.
    Uses suffix arrays to find all possible repetitions.
    """
    n = len(text)
    if n < 2*k:
        return False
        
    # Create suffix array
    suffixes = [(text[i:], i) for i in range(n)]
    suffixes.sort()
    
    # Compare consecutive suffixes to find common prefixes
    for i in range(n-1):
        s1, pos1 = suffixes[i]
        s2, pos2 = suffixes[i+1]
        
        # Find length of common prefix
        common_len = 0
        while common_len < len(s1) and common_len < len(s2) and s1[common_len] == s2[common_len]:
            common_len += 1
            
        # Check if it's a consecutive repetition
        if common_len >= k and abs(pos1 - pos2) == common_len:
            return True
            
    return False

@router.post("/ask")
async def ask(
    request: AskRequest,
    query_engine: QueryEngineInterface = Depends(get_query_engine)
):
    """
    Ask a question within a specific domain.
    """
    try:        
        if request.conversation_id:
            logger.info(f"Processing request for conversation ID: {request.conversation_id}")
        
        if not request.conversation:
            global global_conversation
            # Use the global conversation if the request doesn't provide one
            if global_conversation is None:
                global_conversation = Conversation()
            conversation = global_conversation
        else:
            # Create a new Conversation instance with the provided messages
            conversation = Conversation()
            for msg in request.conversation:
                conversation.add_message(role=msg['role'], content=msg['content'])
        
        full_response = ""
        sources = []
        
        async def content_generator():
            nonlocal full_response, sources
            async for result in await query_engine.ask_question(
                question=request.message,
                model_name=request.genModel,
                conversation=conversation,
                domain_names=None,
                stream=True
            ):
                if isinstance(result, tuple):
                    chunk, chunk_sources = result
                    if chunk_sources is not None:
                        # This is the last message containing sources, don't yield the chunk
                        sources = chunk_sources
                        continue
                else:
                    # If it's not a tuple, it's just a chunk
                    chunk = result

                full_response += chunk
                
                # Check for consecutive repetition
                if has_consecutive_repetition(full_response):
                    error_response = {
                        'content': 'repetition',
                        'type': 'error',
                        'timestamp': time.time()
                    }
                    yield f"data: {json.dumps(error_response)}\n\n"
                    return
                
                response = {
                    'content': chunk, 
                    'type': 'content',
                    'timestamp': time.time()
                }
                yield f"data: {json.dumps(response)}\n\n"
            
            # Add the user's message to the conversation
            conversation.add_message("User", request.message)

            # Add the assistant's message to the conversation
            global_conversation.add_message("Assistant", full_response)
            
            # Update the last response for the avatar
            global last_avatar_response
            last_avatar_response = full_response
            
            done_response = {
                'type': 'done', 
                'timestamp': time.time(),
                'sources': sources
            }
            yield f"data: {json.dumps(done_response)}\n\n"
        
        logging.debug("Successfully generated response, returning StreamingResponse")
        return StreamingResponse(content_generator(), media_type="text/event-stream")
    except Exception as e:
        error_message = str(e)
        logging.error(f"Error in /ask endpoint: {error_message}")
        raise HTTPException(status_code=500, detail=error_message)

@router.post("/init")
async def initialize(
    request: InitRequest,
    query_engine: QueryEngineInterface = Depends(get_query_engine)
):
    """
    Initialize the chat model with the specified generation model.
    """
    try:
        init_prompt = private_settings.prompt.INIT
        full_response = ""
        sources = []

        async def content_generator():
            nonlocal full_response, sources

            async for result in await query_engine.send_initial_message(
                model_name=request.genModel,
                prompt=init_prompt,
                stream=True
            ):
                if isinstance(result, tuple):
                    chunk, chunk_sources = result
                    if chunk_sources is not None:
                        # This is the last message containing sources, don't yield the chunk
                        sources = chunk_sources
                        continue
                else:
                    # If it's not a tuple, it's just a chunk
                    chunk = result

                full_response += chunk
                response = {
                    'content': chunk, 
                    'type': 'content',
                    'timestamp': time.time()
                }
                logging.info(f"Yielding content: {response}")
                yield f"data: {json.dumps(response)}\n\n"
            
            # Add the assistant's message to the conversation
            global_conversation.add_message("Assistant", full_response)
            
            # Update the last response for the avatar
            global last_avatar_response
            last_avatar_response = full_response
            
            done_response = {
                'type': 'done', 
                'timestamp': time.time(),
                #'conversation': [{"role": msg.role, "content": msg.content} for msg in global_conversation.get_history()],
                'sources': sources
            }
            yield f"data: {json.dumps(done_response)}\n\n"
        
        logging.debug("Successfully generated response, returning StreamingResponse")
        return StreamingResponse(content_generator(), media_type="text/event-stream")
    except Exception as e:
        error_message = str(e)
        logging.error(f"Error in /init endpoint: {error_message}")
        raise HTTPException(status_code=500, detail=error_message)

@router.get("/rag_config")
async def rag_config():
    """
    Retrieve the most recent RAG configuration.
    """
    try:
        config_folder = private_settings.CONFIGS_FOLDER
        config_files = glob.glob(os.path.join(config_folder, "config_*.json"))
        
        if not config_files:
            raise HTTPException(status_code=404, detail="No configuration files found")
        
        # Sort files by name (which includes timestamp) in descending order
        latest_config_file = max(config_files)
        
        with open(latest_config_file, "r") as file:
            config_data = json.load(file)
        
        logger.info(f"Successfully retrieved latest RAG configuration: {latest_config_file}")
        return JSONResponse(content=config_data)
    except Exception as e:
        logger.error(f"Error retrieving RAG configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving the configuration")

def merge_configs(base_config: dict, new_config: dict) -> dict:
    """
    Merge two configuration dictionaries. If both dictionaries have the same key
    and their values are lists, sets, or dictionaries, the values are combined.
    """
    merged_config = base_config.copy()
    for key, value in new_config.items():
        logger.debug(f"Processing key: {key}")
        logger.debug(f"Base config value: {merged_config.get(key)} (type: {type(merged_config.get(key))})")
        logger.debug(f"New config value: {value} (type: {type(value)})")
        
        if key in merged_config:
            if isinstance(merged_config[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                merged_config[key] = merge_configs(merged_config[key], value)
                logger.debug(f"Merged dictionary for key '{key}': {merged_config[key]}")
            elif isinstance(merged_config[key], (list, set)) and isinstance(value, (list, set)):
                # Combine the values if both are lists or sets
                merged_config[key] = list(set(merged_config[key]).union(value))
                logger.debug(f"Combined value for key '{key}': {merged_config[key]}")
            else:
                # Overwrite the value if they are not both lists, sets, or dicts

                merged_config[key] = value
                logger.debug(f"Overwritten value for key '{key}': {merged_config[key]}")
        else:
            # Add the new key-value pair
            merged_config[key] = value
            logger.debug(f"Set value for key '{key}': {merged_config[key]}")
    
    return merged_config

async def reload_rag_components():
    """
    Recarga los componentes RAG llamando a la función de inicio.
    """
    from ..rag_app.main import startup_event
    try:
        await startup_event()
        logger.info("Componentes RAG recargados exitosamente")
    except Exception as e:
        logger.error(f"Error recargando componentes RAG: {str(e)}")
        raise

def move_files_preserving_structure(source_folder: Path, dest_folder: Path, timestamp: str):
    """
    Moves entire subdirectories and their contents from source folder to destination folder.
    
    Args:
        source_folder (Path): Source directory path
        dest_folder (Path): Destination directory path
        timestamp (str): Timestamp to append to directory names
    """
    logger.info(f"Moving data")
    try:
        # Iterate through immediate subdirectories only
        for item in source_folder.iterdir():
            logger.info(f"Moving {item}")
            if item.is_dir():
                # Create timestamped directory name
                timestamped_dirname = f"{item.name}_{timestamp}"
                dest_dir = dest_folder / timestamped_dirname
                
                # Create destination directory
                dest_dir.mkdir(parents=True, exist_ok=True)
                
                # Move the entire directory and its contents
                shutil.move(str(item), str(dest_dir))
                logger.info(f"Directory moved to: {dest_dir}")
                
    except Exception as e:
        logger.error(f"Error moving directories: {str(e)}")
        raise

@router.post("/update_RAG_document")
async def update_RAG_document(
    file: UploadFile = File(...),
    domain: str = Form(...)
):
    """
    Update the RAG document by moving the current document to old_data and saving the new document in the data folder.
    Also removes the chroma_db directory and reinitializes RAG setup.
    """
    try:
        # Validate file extension
        allowed_extensions = {'.doc', '.docx', '.pdf', '.PDF'}
        file_ext = Path(file.filename).suffix
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types are: {', '.join(allowed_extensions)}"
            )

        # Setup paths
        data_folder = Path(private_settings.DATA_FOLDER)
        old_data_folder = Path(private_settings.DATA_FOLDER).parent / 'old_data' / domain
        chroma_db_folder = Path(private_settings.DATA_FOLDER).parent / 'chroma_db'
        
        # Create necessary directories
        old_data_folder.mkdir(parents=True, exist_ok=True)
        
        # Move existing files to old_data with timestamp
        domain_folder = data_folder / domain
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        move_files_preserving_structure(data_folder, old_data_folder, timestamp)
            
        # Remove and recreate chroma_db
        if chroma_db_folder.exists():
            shutil.rmtree(chroma_db_folder)
            logger.info(f"Removed chroma_db directory: {chroma_db_folder}")
        
        # Save new file
        domain_folder.mkdir(parents=True, exist_ok=True)
        
        safe_filename = file.filename.replace(" ", "_")
        file_path = domain_folder / safe_filename
        
        # Save file in chunks to handle large files
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"New file saved to: {file_path}")
        
        return {
            "message": "Document updated and RAG reinitialized successfully."
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating RAG document: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating RAG document: {str(e)}"
        )



