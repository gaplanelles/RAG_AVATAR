import logging
import json
import ast
from typing import List, Optional
from src.rag_app.core.interfaces.query_optimizer_interface import QueryOptimizerInterface
from src.rag_app.core.interfaces.chat_model_interface import ChatModelInterface
from src.rag_app.private_config import private_settings

logger = logging.getLogger(__name__)

class QueryOptimizer(QueryOptimizerInterface):
    def __init__(self, chat_model: ChatModelInterface):
        self.chat_model = chat_model
        logger.info("QueryOptimizer initialized")

    async def optimize(self, query: str) -> List[str]:
        """
        Optimize the query using HyDE (Hypothetical Document Embedding) approach.
        Returns a list of optimized queries including the original query.
        """
        logger.info(f"Optimizing query: {query}")
        
        try:
            # Generate hypothetical answers using the chat model
            hyde_prompt = private_settings.prompt.HYDE.format(query=query)
            hyde_response = await self.chat_model.chat(hyde_prompt, query, stream=False)
            
            if hyde_response:
                hypothetical_answers = self._safely_parse_response(hyde_response)
                if hypothetical_answers:
                    optimized_queries = [query] + hypothetical_answers
                    logger.info(f"HyDE generated queries: {hypothetical_answers}")
                    logger.debug(f"Complete set of optimized queries: {optimized_queries}")
                    return optimized_queries
            
        except Exception as e:
            logger.error(f"Error during query optimization: {e}", exc_info=True)
        
        logger.warning("Falling back to original query only")
        return [query]

    def _safely_parse_response(self, response) -> Optional[List[str]]:
        """
        Safely parse the response from the chat model into a list of strings.
        Returns None if parsing fails.
        """
        try:
            # Extract content from response object
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Log the raw content for debugging
            logger.debug(f"Raw content to parse: {content}")
            
            # Try different parsing methods in order of preference
            parsed_content = None
            
            # 1. Try JSON parsing first
            try:
                parsed_content = json.loads(content)
                logger.debug("Successfully parsed content using json.loads()")
            except json.JSONDecodeError as e:
                logger.debug(f"JSON parsing failed: {e}")
                
                # 2. Try ast.literal_eval if JSON parsing fails
                try:
                    parsed_content = ast.literal_eval(content)
                    logger.debug("Successfully parsed content using ast.literal_eval()")
                except (ValueError, SyntaxError) as e:
                    logger.debug(f"ast.literal_eval parsing failed: {e}")
                    
                    # 3. If both fail, try to clean and parse the content
                    clean_content = self._clean_content(content)
                    try:
                        parsed_content = json.loads(clean_content)
                        logger.debug("Successfully parsed cleaned content using json.loads()")
                    except json.JSONDecodeError as e:
                        logger.error(f"All parsing attempts failed. Final error: {e}")
                        logger.error(f"Failed to parse content: {content}")
                        return None
            
            # Validate parsed content
            if isinstance(parsed_content, list):
                # Ensure all elements are strings
                validated_content = [str(item) for item in parsed_content if item]
                if validated_content:
                    return validated_content
                logger.error("Parsed content was empty or contained only empty strings")
            else:
                logger.error(f"Parsed content is not a list. Type: {type(parsed_content)}")
            
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error during response parsing: {e}", exc_info=True)
            return None

    def _clean_content(self, content: str) -> str:
        """
        Clean the content string to make it more amenable to parsing.
        """
        try:
            # Remove any leading/trailing whitespace
            content = content.strip()
            
            # If content is wrapped in quotes, remove them
            if (content.startswith('"') and content.endswith('"')) or \
               (content.startswith("'") and content.endswith("'")):
                content = content[1:-1]
            
            # Replace escaped newlines and quotes
            content = content.replace('\\n', ' ').replace('\\"', '"').replace("\\'", "'")
            
            # Ensure the content is wrapped in square brackets if it isn't already
            if not (content.startswith('[') and content.endswith(']')):
                content = f"[{content}]"
            
            return content
            
        except Exception as e:
            logger.error(f"Error cleaning content: {e}", exc_info=True)
            return content
