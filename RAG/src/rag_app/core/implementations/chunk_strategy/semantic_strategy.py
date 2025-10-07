from typing import List, Dict
import logging
from src.rag_app.core.interfaces.chunk_strategy_interface import ChunkStrategyInterface
from src.rag_app.core.interfaces.embedding_model_interface import EmbeddingModelInterface
from src.rag_app.core.interfaces.document_interface import Chunk

logger = logging.getLogger(__name__)

class SemanticChunkStrategy(ChunkStrategyInterface):
    def __init__(self, embedding_model: EmbeddingModelInterface, max_chunk_size: int = 1024):
        self._strategy_name = "Semantic"
        self.embedding_model = embedding_model
        self.max_chunk_size = max_chunk_size

    @property
    def strategy_name(self) -> str:
        return self._strategy_name

    def get_parameters(self) -> Dict[str, any]:
        return {
            "embedding_model": str(self.embedding_model.model_name),
            "max_chunk_size": self.max_chunk_size
        }

    def chunk_text(self, content: str, document_id: str, doc_path: str) -> List[Chunk]:
        logger.info(f"Applying semantic chunking strategy to document {document_id}")
        
        # Store original content for validation (without extra whitespace)
        original_content = content.strip()
        original_length = len(original_content)
        
        # More comprehensive regex for sentence splitting
        import re
        # Split while preserving all content
        sentences = re.split(r'(?<=[.!?])(\s+)', original_content)  # Keep split delimiters
        sentences = [s for s in sentences if s]  # Remove empty strings

        # Rejoin sentences to validate no data loss
        initial_joined = ''.join(sentences)
        if initial_joined != original_content:
            logger.error("Content loss detected during initial sentence splitting")
            logger.error(f"Original: {repr(original_content)}")
            logger.error(f"Rejoined: {repr(initial_joined)}")
            raise ValueError("Content loss detected during initial split")

        print("No data loss detected. Sentences split successfully.")
        
        # Handle cases where sentences are too long
        processed_sentences = []
        for sentence in sentences:
            if len(sentence) > self.max_chunk_size:
                logger.warning(f"Found sentence longer than max_chunk_size ({len(sentence)} > {self.max_chunk_size})")
                # Store original sentence length for validation
                original_sentence_len = len(sentence)
                
                # Try splitting by semicolon while preserving the delimiter
                sub_parts = [p + ';' for p in sentence.split(';')[:-1]]
                sub_parts.append(sentence.split(';')[-1])  # Add last part without semicolon
                
                if max(len(part) for part in sub_parts) > self.max_chunk_size:
                    # Try splitting by comma while preserving the delimiter
                    sub_parts = [p + ',' for p in sentence.split(',')[:-1]]
                    sub_parts.append(sentence.split(',')[-1])  # Add last part without comma
                    
                    if max(len(part) for part in sub_parts) > self.max_chunk_size:
                        logger.warning("Forcing split by character count")
                        sub_parts = [sentence[i:i + self.max_chunk_size] 
                                   for i in range(0, len(sentence), self.max_chunk_size)]
                
                # Validate sub-parts
                processed_parts = [part for part in sub_parts if part]
                processed_sentence_len = len(''.join(processed_parts))
                
                if processed_sentence_len != original_sentence_len:
                    logger.error(f"Content loss in sentence processing: {original_sentence_len} -> {processed_sentence_len}")
                    raise ValueError("Content loss detected during sentence processing")
                
                processed_sentences.extend(processed_parts)
            else:
                processed_sentences.append(sentence)
        
        # Validate processed sentences
        processed_content = ''.join(processed_sentences)
        
        if len(processed_content) != original_length:
            logger.error("Content length mismatch after processing")
            logger.error(f"Original: {original_length} chars")
            logger.error(f"Processed: {len(processed_content)} chars")
            
            # Write contents to files for debugging
            import os
            debug_dir = "debug_output"
            os.makedirs(debug_dir, exist_ok=True)
            
            with open(os.path.join(debug_dir, f"{document_id}_processed.txt"), "w", encoding="utf-8") as f:
                f.write(processed_content)
            
            with open(os.path.join(debug_dir, f"{document_id}_original.txt"), "w", encoding="utf-8") as f:
                f.write(original_content)
            
            raise ValueError("Content length validation failed")
        
        sentences = processed_sentences
        sentence_ids = list(range(len(sentences)))
        
        embeddings = [self.embedding_model.generate_embedding(sentence) for sentence in sentences]
        similarities = [
            self.embedding_model.calculate_cosine_similarity(embeddings[i], embeddings[i - 1])
            for i in range(1, len(embeddings))
        ]
        
        current_chunk_seq = [0]
        
        def recursive_split(start_idx, end_idx):
            logger.warning(f"Start index: {start_idx}, End index:{end_idx} ")
            if start_idx < end_idx:
                logger.warning(f"Similarities: {similarities[start_idx:end_idx]}")
                logger.warning(f"Similarities max: {max(similarities[start_idx:end_idx])}")
                logger.warning(f"Similarities max index: {similarities[start_idx:end_idx].index(max(similarities[start_idx:end_idx]))}")
                logger.warning(f"Similarities max index absol: {start_idx + similarities[start_idx:end_idx].index(max(similarities[start_idx:end_idx]))}")
            if start_idx > end_idx:
                logger.error("Start index is greater than end index.")
                return []
            
            chunk_content = ' '.join(sentences[start_idx:end_idx + 1])
            
            # If chunk is within size limit, create chunk
            logger.warning(f"Length chunk size: {len(chunk_content)} ")
            logger.warning(f"Chunk content: {chunk_content} ")
            if len(chunk_content) <= self.max_chunk_size:
                chunk_seq = current_chunk_seq[0]
                current_chunk_seq[0] += 1
                logger.warning(f"Saving chunks...")
                return [Chunk(
                    document_id=document_id,
                    chunk_id=f"{document_id}_{chunk_seq}",
                    content=chunk_content,
                    metadata={
                        "start_sentence": start_idx,
                        "end_sentence": end_idx,
                        "forced_split": False
                    }
                )]
            else:
                logger.warning(f"chunk size limit exceded.")
            
            # If we can't split further (only one sentence), force create the chunk
            if start_idx == end_idx:
                logger.warning(f"Forced to create oversized chunk: {len(chunk_content)} characters")
                chunk_seq = current_chunk_seq[0]
                current_chunk_seq[0] += 1
                return [Chunk(
                    document_id=document_id,
                    chunk_id=f"{document_id}_{chunk_seq}",
                    content=chunk_content,
                    metadata={
                        "start_sentence": start_idx,
                        "end_sentence": end_idx,
                        "forced_split": True
                    }
                )]
            
            # Find split point based on similarity
            max_similarity_idx = start_idx + similarities[start_idx:end_idx].index(max(similarities[start_idx:end_idx]))
            logger.warning(f"Maximum similarity index: {max_similarity_idx}")
            
            return recursive_split(start_idx, max_similarity_idx) + recursive_split(max_similarity_idx + 1, end_idx)
        
        chunks = recursive_split(0, len(sentences) - 1)
        
        return chunks

    async def format_result(self, data_path, combined_results: List[dict], result_domains: List[str]) -> List[dict]:
        return combined_results