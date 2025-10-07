from typing import List, Dict
import logging
from src.rag_app.core.interfaces.chunk_strategy_interface import ChunkStrategyInterface
from src.rag_app.core.interfaces.document_interface import Chunk
from PyPDF2 import PdfReader
import os

logger = logging.getLogger(__name__)

class FixedSizeChunkStrategy(ChunkStrategyInterface):
    def __init__(self, chunk_size: int, overlap: int = 0):
        self._strategy_name = "Fixed Size"
        self.chunk_size = chunk_size
        self.overlap = overlap

    @property
    def strategy_name(self) -> str:
        return self._strategy_name

    def get_parameters(self) -> Dict[str, any]:
        return {
            "chunk_size": self.chunk_size,
            "overlap": self.overlap
        }

    def chunk_text(self, content: str, document_id: str, doc_path: str) -> List[Chunk]:
        if content is None:
            logger.warning("Received None content in chunk_text method")
            return []
        
        chunks = []
        _, file_extension = os.path.splitext(doc_path)
        file_extension = file_extension.lower()
        chunk_id = 0

        if file_extension == '.pdf':
            try:
                with open(doc_path, 'rb') as f:
                    pdf = PdfReader(f)
                    page_texts = [page.extract_text() or '' for page in pdf.pages]
                    full_text = '\n'.join(page_texts)
                    # Build a list of (start, end, page_number) for each page
                    page_boundaries = []
                    cursor = 0
                    for i, text in enumerate(page_texts):
                        length = len(text)
                        page_boundaries.append((cursor, cursor + length, i + 1))
                        cursor += length + 1  # +1 for the '\n' join
                    start = 0
                    content_length = len(full_text)
                    while start < content_length:
                        end = start + self.chunk_size
                        chunk_content = full_text[start:end]
                        # Find all page numbers that overlap with this chunk
                        page_numbers = []
                        for (p_start, p_end, p_num) in page_boundaries:
                            if not (end <= p_start or start >= p_end):
                                page_numbers.append(p_num)
                        # Convert to unique, sorted, comma-separated string
                        page_numbers_str = ','.join(str(num) for num in sorted(set(page_numbers)))
                        metadata = {"start": start, "end": end, "page_number": page_numbers_str}
                        chunk = Chunk(
                            document_id=document_id,
                            chunk_id=f"{document_id}_chunk_{chunk_id}",
                            metadata=metadata,
                            content=chunk_content
                        )
                        chunks.append(chunk)
                        start = end - self.overlap
                        chunk_id += 1
            except Exception as e:
                logger.error(f"Error reading PDF for chunking: {e}")
        else:
            start = 0
            content_length = len(content)
            while start < content_length:
                end = start + self.chunk_size
                chunk_content = content[start:end]
                metadata = {"start": start, "end": end}
                chunk = Chunk(
                    document_id=document_id,
                    chunk_id=f"{document_id}_chunk_{chunk_id}",
                    metadata=metadata,
                    content=chunk_content
                )
                chunks.append(chunk)
                start = end - self.overlap
                chunk_id += 1
        
        return chunks

    async def format_result(self, data_path, combined_results: List[dict], result_domains: List[str]) -> List[dict]:
        return combined_results