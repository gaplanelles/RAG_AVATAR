from typing import List, Union, Dict, Optional
import logging
from ...interfaces.embedding_model_interface import EmbeddingModelInterface
from langchain_community.embeddings import OCIGenAIEmbeddings

logger = logging.getLogger(__name__)

class OCIEmbedding(EmbeddingModelInterface):
    def __init__(self, settings: Dict[str, Union[str, int, float]]):
        logger.info("Initializing OCI embedding model")
        logger.info(f"With model {settings['MODEL_NAME']}")
        
        self._model_name = settings["MODEL_NAME"]
        
        embedding_params = {
            "model_id": settings["MODEL_NAME"],
            "service_endpoint": settings["OCI_GENAI_ENDPOINT"],
            "compartment_id": settings["OCI_COMPARTMENT_ID"],
            "auth_type": "API_KEY",
            "auth_profile": settings["OCI_CONFIG_PROFILE"]
        }
        
        self._embedding_model = OCIGenAIEmbeddings(**embedding_params)

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_embedding(self, chunks: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        if isinstance(chunks, str):
            chunks = [chunks]
        
        logger.debug(f"Generating embeddings for {len(chunks)} chunk(s)")
        
        try:
            embeddings = self._embedding_model.embed_documents(chunks)
            return embeddings[0] if len(embeddings) == 1 else embeddings
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
