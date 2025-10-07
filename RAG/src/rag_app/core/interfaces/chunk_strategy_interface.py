from abc import ABC, abstractmethod
from typing import List, Dict
from src.rag_app.core.interfaces.document_interface import Chunk

class ChunkStrategyInterface(ABC):
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, any]:
        pass

    @abstractmethod
    def chunk_text(self, content: str, document_id: str, doc_path: str | None = None) -> List[Chunk]:
        pass
