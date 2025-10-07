import os
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Optional
from .prompts import PromptSettings, prompt_settings
import logging

class ChatModelSettings(BaseModel):
    # OCI settings
    OCI_COMPARTMENT_ID: str
    OCI_GENAI_ENDPOINT: str
    OCI_CONFIG_PROFILE: str
    OCI_CONFIG_PATH: str = "~/.oci/config"
    OCI_CHAT_DEFAULT_MODEL: str

class EmbeddingModelSettings(BaseModel):
    OLLAMA_HOST: str
    OLLAMA_PORT: int = 11434
    OCI_COMPARTMENT_ID: str
    OCI_GENAI_ENDPOINT: str
    OCI_CONFIG_PROFILE: str
    OCI_CONFIG_PATH: str
    OCI_EMBEDDINGS_DEFAULT_MODEL: str

class VectorStoreSettings(BaseModel):
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"

class DocumentSettings(BaseModel):
    DB_CONNECTION_STRING: Optional[str] = None

class PrivateSettings(BaseSettings):
    # Basic settings
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    COHERE_API_KEY: str
    BACKEND_PORT: int
    FRONTEND_URL: str

    # OCI settings that will be used in nested models
    OCI_COMPARTMENT_ID: str
    OCI_GENAI_ENDPOINT: str
    OCI_CONFIG_PROFILE: str
    OCI_CONFIG_PATH: str
    OCI_CHAT_DEFAULT_MODEL: str
    OCI_EMBEDDINGS_DEFAULT_MODEL: str

    # Ollama settings that will be used in nested models
    OLLAMA_HOST: str
    OLLAMA_PORT: int = 11434

    # Folder paths
    DATA_FOLDER: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    DOCS_FOLDER: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs")
    CONFIGS_FOLDER: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "configs")

    # Nested settings with default None
    chat_model: Optional[ChatModelSettings] = None
    embedding_model: Optional[EmbeddingModelSettings] = None
    vector_store: VectorStoreSettings = VectorStoreSettings()
    document: DocumentSettings = DocumentSettings()

    # Prompts
    prompt: PromptSettings = prompt_settings

    # Logging settings
    LOG_FILE_NAME: str = "rag_app.log"
    LOG_DIR: str = "logs"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 5

    # CORS Settings
    CORS_ALLOW_ORIGINS: list[str] = ["http://139.185.59.9:9002", "https://aion-czech.netlify.app"]
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "OPTIONS"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_MAX_AGE: int = 600

    @property
    def cors_origins(self) -> list[str]:
        """Returns list of allowed origins, always including FRONTEND_URL if set"""
        origins = self.CORS_ALLOW_ORIGINS.copy()
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)

        # Extract port from FRONTEND_URL and append localhost with that port
        if self.FRONTEND_URL:
            port = self.FRONTEND_URL.split(':')[-1]
            localhost_url = f"http://localhost:{port}"
            if localhost_url not in origins:
                origins.append(localhost_url)

        logging.info(f"cors_origins{origins}")
        return origins

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"  # This allows nested config from env vars
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Create DATA_FOLDER if it doesn't exist
        os.makedirs(self.DATA_FOLDER, exist_ok=True)
        
        # Initialize nested models after parent initialization
        self.chat_model = ChatModelSettings(
            OCI_COMPARTMENT_ID=self.OCI_COMPARTMENT_ID,
            OCI_GENAI_ENDPOINT=self.OCI_GENAI_ENDPOINT,
            OCI_CONFIG_PROFILE=self.OCI_CONFIG_PROFILE,
            OCI_CONFIG_PATH=self.OCI_CONFIG_PATH,
            OCI_CHAT_DEFAULT_MODEL=self.OCI_CHAT_DEFAULT_MODEL,
        )
        self.embedding_model = EmbeddingModelSettings(
            OLLAMA_HOST=self.OLLAMA_HOST,
            OLLAMA_PORT=self.OLLAMA_PORT,
            OCI_COMPARTMENT_ID=self.OCI_COMPARTMENT_ID,
            OCI_GENAI_ENDPOINT=self.OCI_GENAI_ENDPOINT,
            OCI_CONFIG_PROFILE=self.OCI_CONFIG_PROFILE,
            OCI_CONFIG_PATH=self.OCI_CONFIG_PATH,
            OCI_EMBEDDINGS_DEFAULT_MODEL=self.OCI_EMBEDDINGS_DEFAULT_MODEL,
        )

private_settings = PrivateSettings()
