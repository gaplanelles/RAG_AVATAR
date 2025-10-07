import logging
from typing import List, Dict, Any, AsyncGenerator, Optional, Iterator, Union, AsyncIterator, Tuple
from ...interfaces.query_engine_interface import QueryEngineInterface
from ...interfaces.domain_manager_interface import DomainManagerInterface
from ...interfaces.vector_store_interface import VectorStoreInterface
from ...interfaces.query_optimizer_interface import QueryOptimizerInterface
from ...interfaces.reranker_interface import ReRankerInterface
from ...interfaces.embedding_model_interface import EmbeddingModelInterface
from ...interfaces.chat_model_interface import ChatModelInterface
from ...interfaces.chunk_strategy_interface import ChunkStrategyInterface
from ...interfaces.conversation_interface import ConversationInterface

from rag_app.private_config import private_settings
import time
import json
import os

logger = logging.getLogger(__name__)

class QueryEngine(QueryEngineInterface):
    def __init__(self, 
                 domain_manager: DomainManagerInterface, 
                 vector_stores: Dict[str, VectorStoreInterface], 
                 embedding_model: EmbeddingModelInterface,
                 chat_model: ChatModelInterface,
                 chunk_strategy: ChunkStrategyInterface,
                 query_optimizer: QueryOptimizerInterface,
                 result_re_ranker: ReRankerInterface,
                 n_results: int = 10): #here we can change the number of results
        self.domain_manager = domain_manager
        self.vector_stores = vector_stores
        self.embedding_model = embedding_model
        self.chat_model = chat_model
        self.query_optimizer = query_optimizer
        self.result_re_ranker = result_re_ranker
        self.n_results = n_results
        self.chunk_strategy = chunk_strategy
        self.last_results = None
        logger.info("QueryEngine initialized")

    @property
    def n_results(self) -> int:
        return self._n_results

    @n_results.setter
    def n_results(self, value: int):
        if not isinstance(value, int) or value <= 0:
            raise ValueError("n_results must be a positive integer")
        self._n_results = value
        logger.debug(f"n_results updated to {value}")

    async def send_initial_message(self, model_name: str, prompt: str, stream: bool = True) -> Union[str, AsyncIterator[str]]:
        """
        Send the initial prompt to the chat model and yield responses in chunks.
        """
        logger.debug(f"Sending initial message with model: {model_name}")
        response = await self.chat_model.chat(prompt, "", stream=stream)
        
        if stream:
            return self._stream_response(response, sources=[])
        else:
            return response.content if hasattr(response, 'content') else str(response)

    async def ask_question(
        self, 
        question: str, 
        domain_names: Optional[List[str]] = None, 
        model_name: str = "OCI_CommandRplus",
        conversation: ConversationInterface = None, 
        stream: bool = True
    ) -> Union[Tuple[str, List], AsyncIterator[Tuple[str, List]]]:
        """
        Ask a question across multiple domains and stream the response in chunks.

        :param question: The user's question.
        :param domain_names: List of domain names to query. If None, query all available domains.
        :param conversation: The conversation interface.
        :param stream: Whether to stream the response.
        :return: The answer as a string or an asynchronous iterator of string chunks.
        """
        logger.debug(f"Processing question: '{question}'")

        # Validate domains
        domain_names = await self._validate_domains(domain_names)
        
        # Get optimized queries based on configuration
        queries_to_process = await self._get_queries(question)
        
        # Process queries and collect results
        combined_results = await self._process_queries(queries_to_process, domain_names)

        # Process results and generate response
        return await self._generate_response(question, combined_results, conversation, stream)

    async def _validate_domains(self, domain_names: Optional[List[str]]) -> List[str]:
        """Validate and return list of domains to query."""
        if domain_names is None:
            domain_names = list(self.domain_manager.vector_stores.keys())
            logger.debug(f"No specific domains provided. Using all domains: {domain_names}")
        else:
            invalid_domains = [d for d in domain_names if d not in self.domain_manager.vector_stores]
            if invalid_domains:
                error_msg = f"Invalid domains specified: {invalid_domains}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            logger.debug(f"Using specified domains: {domain_names}")
        return domain_names

    async def _get_queries(self, question: str) -> List[str]:
        """Get list of queries to process based on configuration."""
        #if self.query_optimizer is not None:
        if False:
            logger.info("Using HyDE optimization")
            return await self.query_optimizer.optimize(question)
        logger.debug("Using original query only")
        return [question]
    
    def _generate_adjacent_chunk_ids(self, chunk_ids: List[str]) -> List[str]:
        """Generate previous and next chunk IDs for each chunk ID in the list."""
        all_ids = set()  
        
        for chunk_id in chunk_ids:
            try:
               
                parts = chunk_id.rsplit('_', 1) 
                base = parts[0]  
                current_num = int(parts[1])  
                
                
                prev_id = f"{base}_{current_num - 1}"
                next_id = f"{base}_{current_num + 1}"
                
                
                all_ids.add(chunk_id)  
                all_ids.add(prev_id)   
                all_ids.add(next_id)   
                
            except Exception as e:
                logger.error(f"Error processing chunk ID {chunk_id}: {str(e)}")
    
        
        return list(all_ids)
    
    def _get_chunk_content(self, vector_store, chunk_id: str) -> str:
        """Helper function to get chunk content safely."""
        try:
            result = vector_store.collection.get(
                ids=[chunk_id],
                include=['documents']
            )
            return result['documents'][0] if result and result['documents'] else ""
        except Exception as e:
            logger.warning(f"Could not retrieve chunk {chunk_id}: {str(e)}")
            return ""

    def _combine_adjacent_chunks(self, vector_store, chunk_id: str, distance: float = None) -> dict:
        """Combine content of previous, current and next chunks while maintaining original chunk structure."""
        import json
        import glob
        import os
        
        # Obtener el archivo de configuración más reciente
        config_path = "/home/ubuntu/gonareva/RAG-IDIKA-2CTORS/RAG/configs"
        config_files = glob.glob(os.path.join(config_path, "*.json"))
        latest_config = max(config_files, key=os.path.getctime)
        
        # Leer la configuración
        with open(latest_config, 'r') as f:
            config = json.load(f)
        
        
        chunk_overlap = config['chunking']['CHUNK_OVERLAP']
        logger.debug(f"Chunk overlap: {chunk_overlap}")

        parts = chunk_id.rsplit('_', 1)
        base = parts[0]
        current_num = int(parts[1])
        prev_id = f"{base}_{current_num - 1}"
        next_id = f"{base}_{current_num + 1}"
        
        prev_content = self._get_chunk_content(vector_store, prev_id)
        if prev_content:
            prev_content = prev_content[:-chunk_overlap]
        logger.debug(f"Previous content: {prev_content}")
        current_content = self._get_chunk_content(vector_store, chunk_id)
        logger.debug(f"Current content: {current_content}")
        next_content = self._get_chunk_content(vector_store, next_id)
        if next_content:
            next_content = next_content[chunk_overlap:]
        logger.debug(f"Next content: {next_content}")
        
        original_result = vector_store.collection.get(
            ids=[chunk_id],
            include=['documents', 'metadatas']
        )
        
        if not original_result or not original_result['documents']:
            return None

        # Combine the contents
        combined_document = f"{prev_content}\n\n{current_content}\n\n{next_content}"
        
        # Create result maintaining original structure with distance
        combined_result = {
            'id': chunk_id,
            'distance': distance,  # Include the distance from the original result
            'document': combined_document,
            'metadata': original_result['metadatas']
            #'metadata': original_result['metadatas'][0] if original_result.get('metadatas') else {}
        }
        
        logger.debug(f"Combined chunks for {chunk_id}")
        return combined_result
    
    def _combine_structured_adjacent_chunks(self, vector_store, chunk_id: str, distance: float = None) -> dict:
        """Combine content of previous, current and next chunks while maintaining original chunk structure."""
        import json
        import glob
        import os
        
        # Obtener el archivo de configuración más reciente
        config_path = "/home/ubuntu/gonareva/RAG-IDIKA-2CTORS/RAG/configs"
        config_files = glob.glob(os.path.join(config_path, "*.json"))
        latest_config = max(config_files, key=os.path.getctime)
        
        # Leer la configuración
        with open(latest_config, 'r') as f:
            config = json.load(f)
        
        
        chunk_overlap = config['chunking']['CHUNK_OVERLAP']
        logger.debug(f"Chunk overlap: {chunk_overlap}")

        parts = chunk_id.rsplit('_', 1)
        base = parts[0]
        current_num = int(parts[1])
        prev_id = f"{base}_{current_num - 1}"
        next_id = f"{base}_{current_num + 1}"
        
        prev_content = self._get_chunk_content(vector_store, prev_id)
        if prev_content:
            prev_content = prev_content[:-chunk_overlap]
        logger.debug(f"Previous content: {prev_content}")
        current_content = self._get_chunk_content(vector_store, chunk_id)
        logger.debug(f"Current content: {current_content}")
        next_content = self._get_chunk_content(vector_store, next_id)
        if next_content:
            next_content = next_content[chunk_overlap:]
        logger.debug(f"Next content: {next_content}")
        
        original_result = vector_store.collection.get(
            ids=[chunk_id],
            include=['documents', 'metadatas']
        )
        
        if not original_result or not original_result['documents']:
            return None

        # Combine the contents
        combined_document = f"{prev_content}\n\n{current_content}\n\n{next_content}"
        
        # Create result maintaining original structure with distance
        combined_result = {
            'id': chunk_id,
            'distance': distance,  # Include the distance from the original result
            'document': combined_document,
            'metadata': original_result['metadatas']
            #'metadata': original_result['metadatas'][0] if original_result.get('metadatas') else {}
        }
        
        logger.debug(f"Combined chunks for {chunk_id}")
        return combined_result
    
    async def _process_queries(self, queries: List[str], domain_names: List[str]) -> List[dict]:
        """Process all queries across specified domains."""
        combined_results = []
        result_domains = []  # List to track domains for each result
        
        for domain_name in domain_names:
            #logger.info(f"Querying domain: {domain_name}")
            vector_store = self.domain_manager.vector_stores[domain_name]
            
            for query in queries:
                query_embedding = self.embedding_model.generate_embedding(query)
                results = vector_store.query(
                    query_embedding=query_embedding, 
                    n_results=self.n_results
                )
                #logger.info(f"Query results from chromadb: {results}")
                
                # Append results with domain context
                for result in results:
                    result['domain'] = domain_name
                    combined_results.append(result)
                    result_domains.append(domain_name)
        
        # Format results based on chunk strategy, passing all relevant domains
        formatted_results = await self.chunk_strategy.format_result(data_path = private_settings.DATA_FOLDER, combined_results = combined_results, result_domains = result_domains)
        
        return formatted_results
    
    async def _generate_response(
        self, 
        question: str, 
        combined_results: List[dict], 
        conversation: Optional[ConversationInterface],
        stream: bool
    ) -> Union[Tuple[str, List], AsyncIterator[Tuple[str, List]]]:
        """Generate final response from processed results."""
        # Re-rank results if available
        if self.result_re_ranker is not None:
            ranked_results = self.result_re_ranker.re_rank(combined_results, question)
        else:
            ranked_results = combined_results

        """
        if not ranked_results and not self.last_results:
            context = private_settings.prompt.NO_RESULTS
        elif not ranked_results and self.last_results:
            context = private_settings.prompt.USING_LAST_RESULTS.format(
                last_results="\n".join([result["document"] for result in self.last_results[:self.n_results]])
            )
        else:
            context = "\n".join([result["document"] for result in ranked_results[:self.n_results]])
        """

        if not ranked_results:
            context = private_settings.prompt.NO_RESULTS
        else:
            context_chunks = []
            for idx, result in enumerate(ranked_results[:self.n_results]):
                if idx == 0:
                    header = f"""#### Partie {idx + 1} trouvée (plus pertinente) \n
                    Document: {result['metadata']['document_name']} \n
                    """

                else:
                    header = f"#### Partie {idx + 1} trouvée"
                context_chunks.append(f"{header}\n{result['document']}")
            context = "\n\n".join(context_chunks)
            
        prompt = private_settings.prompt.QUESTION.format(context=context, query=question)
        
        if ranked_results:
            self.last_results = ranked_results
        else:
            self.last_results = []

        logger.debug("Processing question")
        #logger.info(f"Risposta in document {ranked_results[0]['metadata']['document_name']}")
        logger.info("Generating response from chat model")
        response = await self.chat_model.chat(
            system_prompt=prompt, 
            query=question, 
            conversation=conversation, 
            stream=stream
        )

        if stream:
            return self._stream_response(response, ranked_results)
        else:
            full_response = await response
            return full_response, ranked_results

    def initialize_chat_model(self, gen_model: str, init_prompt: str) -> Dict[str, Any]:
        """
        Initialize the chat model with the provided generation model and initial prompt.
        """
        logger.debug(f"Initializing chat model with model: {gen_model}")
        try:
            # Here you might have specific initialization logic based on the model
            prompt = init_prompt
            response = self.chat_model.generate_response(prompt)
            logger.debug("Chat model initialized successfully.")
            return {"message": response}
        except Exception as e:
            logger.error(f"Failed to initialize chat model: {str(e)}")
            raise

    async def _stream_response(self, response: AsyncIterator[str], sources: List) -> AsyncIterator[Tuple[str, List]]:
        async for chunk in response:
            yield chunk, None
        yield "", sources