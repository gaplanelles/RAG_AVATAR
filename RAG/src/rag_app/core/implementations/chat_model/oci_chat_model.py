import logging
from abc import ABC, abstractmethod
from langchain_community.chat_models import ChatOCIGenAI
from langchain_core.prompts import PromptTemplate
from typing import Optional, Iterator, Union, AsyncIterator
import oci
from rag_app.core.interfaces.chat_model_interface import ChatModelInterface
from ...interfaces.conversation_interface import ConversationInterface
from rag_app.core.implementations.conversation.conversation import Conversation
import random

# Enable debug logging for the entire oci package
# logging.getLogger('oci').setLevel(logging.DEBUG)

# Enable request logging
oci.base_client.is_http_log_enabled(False)

logger = logging.getLogger(__name__)
logging.getLogger("oci").setLevel(logging.CRITICAL)


class ChatModel(ChatModelInterface):
    @abstractmethod
    def __init__(self):
        pass

    @property
    @abstractmethod
    def llm(self):
        pass

    @staticmethod
    def _process_model_params(settings: dict, keys_with_defaults: dict) -> dict:
        """
        Process model parameters, normalizing keys to lowercase and applying defaults.

        Args:
            settings (dict): The configuration dictionary, where keys are in uppercase.
            keys_with_defaults (dict): A dictionary of expected keys and their default values.

        Returns:
            dict: Processed model parameters with lowercase keys and applied defaults.
        """

        return {
            key.lower(): settings.get(key.upper(), default)
            for key, default in keys_with_defaults.items()
        }

    async def chat(
        self,
        system_prompt: str,
        query: str,
        conversation: Optional[ConversationInterface] = Conversation(),
        stream: bool = False,
    ) -> Union[str, AsyncIterator[str]]:
        prompt_template = f"{system_prompt}\n\n"
        # logger.info(f"System prompt:\n\n {prompt_template}\n\n")

        # if conversation:
        if conversation.get_formatted_history() != "":
            prompt_template += "### Histoire de la conversation \n\n"
            prompt_template += f"{conversation.get_formatted_history()}\n\n"

        if query == "":
            logger.info("query empty")
        
        prompt = PromptTemplate(input_variables=["query"], template=prompt_template)
        # Log the final prompt
        history = conversation.get_formatted_history()

        # logger.info(f"History:\n\n {history}\n\n")
        # logger.info(f"Final prompt: {prompt.format(query=query)}")
        formatted_prompt = prompt.template.format(query=query)
        logger.info(f"Final prompt (system prompt + query + history) \n {formatted_prompt}")

        # logger.info(f"full_prompt: {prompt}")

        llm_chain = prompt | self.llm

        if stream:
            return self._stream_response(llm_chain, query)
        else:
            return await self._generate_response(llm_chain, query)

    async def _generate_response(self, llm_chain, query: str) -> str:
        logger.debug(
            f"Generating response with {self.__class__.__name__} for query: {query[:50]}..."
        )
        response = await llm_chain.ainvoke({"query": query})

        return response

    async def _stream_response(self, llm_chain, query: str) -> AsyncIterator[str]:
        logger.debug(
            f"Streaming response with {self.__class__.__name__} for query: {query[:50]}..."
        )
        full_response = ""
        buffer = ""
        is_fixing = False

        async for chunk in llm_chain.astream({"query": query}):
            if chunk.content is None:
                continue

            # If you need to simulate the characters issue, remove comments from 85 to 97, and substitute 179 and 180

            # Replace a random character with two symbols with 5% probability
            # modified_content = chunk.content
            # helen msg
            # logger.info(f"Modified content is: {modified_content}")
            # if random.random() < 0.01 and len(modified_content) > 0:  # 5% chance and non-empty content
            #    replace_index = random.randint(0, len(modified_content) - 1)
            #    modified_content = (
            #        modified_content[:replace_index] +
            #        "��" +
            #        modified_content[replace_index + 1:]
            #    )
            #    logger.warning(f"Replaced character at index {replace_index} with malformed characters")

            # chunk.content = modified_content

            # Log raw chunk content and its UTF representation
            # logger.debug("Raw chunk content")
            # logger.info(f"Raw chunk content (repr): {repr(chunk.content)}")
            # logger.info(f"Raw chunk content: {(chunk.content)}")
            # logger.info(f"UTF-8 bytes: {chunk.content.encode('utf-8')}")
            # logger.info(f"UTF-16 bytes: {chunk.content.encode('utf-16')}")
            # logger.info(f"UTF-8 content: {chunk.content.encode('utf-8').decode('utf-8')}")
            # logger.info(f"UTF-16 content: {chunk.content.encode('utf-16').decode('utf-16')}")
            # logger.info(f"UTF-16 little-endian bytes encodede: {chunk.content.encode('utf-16le')}")
            # logger.info(f"UTF-16 little-endian bytes decoded: {chunk.content.encode('utf-16le').decode('utf-16le')}")

            # If we're already collecting a malformed word
            if is_fixing:
                buffer += chunk.content
                # Check for termination conditions
                is_done = getattr(chunk, "type", None) == "done"
                has_terminator = any(term in chunk.content for term in [" ", ". "])

                if has_terminator or is_done:
                    # Find where the word ends
                    end_idx = len(buffer)
                    if " " in chunk.content:
                        end_idx = buffer.rindex(" ")
                    elif ". " in chunk.content:
                        end_idx = buffer.rindex(". ") + 1  # Include the period

                    malformed_text = buffer[:end_idx]
                    remaining_text = buffer[end_idx:]

                    # Fix the malformed word
                    ###############################################
                    # Francesco
                    ###############################################
                    # context = full_response if full_response else ""
                    # has_leading_space = malformed_text.startswith(" ")
                    # fixed_word = await self._fix_malformed_word(malformed_text, context)

                    # Add leading space if it was in the original but missing in the fixed word
                    # if has_leading_space and not fixed_word.startswith(" "):
                    #    fixed_word = " " + fixed_word

                    # logger.warning(f"Fixed malformed word: {malformed_text} -> {fixed_word}")

                    # Yield the fixed content
                    # full_response += fixed_word
                    # yield "_"+fixed_word

                    ###############################################
                    # Gonzalo
                    ###############################################
                    context = full_response if full_response else ""
                    has_leading_space = malformed_text.startswith(" ")

                    # Calcular caracteres desde el último espacio
                    last_space_index = context.rstrip().rfind(" ")
                    chars_after_space = (
                        len(context) - last_space_index - 1
                        if last_space_index != -1
                        else 0
                    )
                    logger.warning(
                        f"Chars after the last space in context: {chars_after_space} "
                    )
                    text_after_last_space = (
                        context[last_space_index + 1 :]
                        if last_space_index != -1
                        else context
                    )
                    num_escape_chars = sum(
                        1
                        for char in text_after_last_space
                        if char in ["'", '"', "(", "´"]
                    )
                    chars_after_space = chars_after_space - num_escape_chars
                    fixed_word = await self._fix_malformed_word(malformed_text, context)

                    # Add leading space if it was in the original but missing in the fixed word
                    if has_leading_space and not fixed_word.startswith(" "):
                        fixed_word = " " + fixed_word
                        chars_after_space = 0

                    logger.warning(
                        f"Fixed malformed word: {malformed_text} -> {fixed_word}"
                    )
                    logger.warning(
                        f"number of escape chars (parenthesis, quote, or double quotes) after the last space in context: {num_escape_chars} "
                    )
                    logger.warning(f"Chars to be removed: {chars_after_space} ")
                    logger.warning(f"We will send: {fixed_word[chars_after_space:]} ")

                    # Extract any special characters at the end of malformed_text
                    special_chars = ""
                    if malformed_text.endswith(('"', "'", ")", "´")):
                        special_chars = malformed_text[-1]
                        # Remove the special char from fixed_word if it's there
                        fixed_word = (
                            fixed_word[:-1]
                            if fixed_word.endswith(special_chars)
                            else fixed_word
                        )

                    # logger.info(f"Full response b4 is: {full_response}")
                    full_response += fixed_word + special_chars
                    # yield "_" + fixed_word[chars_after_space:] + special_chars
                    yield fixed_word[chars_after_space:] + special_chars

                    # Reset fixing state
                    is_fixing = False
                    buffer = remaining_text

                    # If we have remaining text, yield it
                    if remaining_text:
                        full_response += remaining_text
                        yield remaining_text

                    continue

                # If no termination found, continue collecting
                continue

            # Check for malformed characters in new chunk
            if "�" in chunk.content:
                logger.warning(
                    f"Detected malformed character in chunk: {chunk.content}"
                )
                buffer = chunk.content
                is_fixing = True
                continue

            # Normal streaming when no issues
            try:
                cleaned_content = chunk.content.encode("utf-8", errors="ignore").decode(
                    "utf-8"
                )
                full_response += cleaned_content
                yield cleaned_content
            except Exception as e:
                logger.warning(f"Error processing chunk content: {e}")
                full_response += chunk.content
                yield chunk.content

        logger.debug(f"Complete response: {full_response}")

    async def _fix_malformed_word(self, malformed_text: str, context: str) -> str:
        """
        Attempts to fix a malformed word by asking the LLM for the correct word given the context.

        Args:
            malformed_text: The text containing the malformed word
            context: The surrounding context to help determine the correct word

        Returns:
            The corrected word
        """
        system_prompt = """Είστε ένας εξειδικευμένος γλωσσικός βοηθός που διορθώνει χαλασμένες ελληνικές λέξεις.
        ΣΗΜΑΝΤΙΚΟ: Πρέπει να επιστρέψετε ΜΟΝΟ το διορθωμένο μέρος της λέξης, χωρίς περαιτέρω εξηγήσεις ή σχόλια.
        ΑΝ ΥΠΑΡΧΟΥΝ κενά ή σημεία στίξης στο τέλος, πρέπει να διατηρηθούν όπως είναι."""

        query = f"""Δεδομένου του παρακάτω κειμένου που περιέχει μια κατεστραμμένη λέξη: "{malformed_text}"

        Και λαμβάνοντας υπόψη το ακόλουθο πλαίσιο κειμένου που τελειώνει πριν τη λέξη: {context[-50:]}{malformed_text}

        Συμπληρώστε τη σωστή ελληνική λέξη.
        Απαντήστε μόνο με τη διορθωμένη εκδοχή της λέξης "{malformed_text}" ολόκληρη, χωρίς να προσθέσετε επιπλέον κενά ή σημεία στίξης.
        """

        # Log the complete prompt for debugging
        logger.warning(
            f"Malformed word fix prompt:\nSystem: {system_prompt}\nQuery: {query}"
        )

        # Use the chat method with stream=False
        response = await self.chat(
            system_prompt=system_prompt, query=query, stream=False
        )

        # Clean any potential whitespace or newlines
        fixed_word = response.content
        logger.warning(f"Fixed word response: '{fixed_word}'")

        return fixed_word


class OCI_CommandRplus(ChatModel, ChatModelInterface):
    def __init__(self, settings: dict):
        logger.debug(f"Initializing {self.__class__.__name__} chat model")

        # Define the expected keys and their default values
        default_model_params = {
            "temperature": 0,
            "max_tokens": 4000,
            "top_p": 0,
            "top_k": 1,
            "seed": 42,
        }

        model_kwargs = self._process_model_params(settings, default_model_params)
        logger.info(
            f"Model {self.__class__.__name__} initializing with model parameters: {model_kwargs}"
        )

        # Use the settings dictionary to fetch parameters
        llm_params = {
            # "model_id": "ocid1.generativeaimodel.oc1.eu-frankfurt-1.amaaaaaask7dceyabdu6rjjmg75pixtecqvjen4x4st4mhs2a4zzfx5cgkmq", #settings["MODEL_ID"], #cohere.command-r-plus-08-2024
            # "provider": "cohere",
            "model_id": settings["MODEL_ID"],
            "service_endpoint": settings["OCI_GENAI_ENDPOINT"],
            "compartment_id": settings["OCI_COMPARTMENT_ID"],
            "auth_type": "API_KEY",
            "auth_profile": settings["OCI_CONFIG_PROFILE"],
            "model_kwargs": model_kwargs,
        }

        self._llm = ChatOCIGenAI(**llm_params)

    @property
    def llm(self):
        return self._llm


class OCI_Llama3_70(ChatModel, ChatModelInterface):
    def __init__(self, settings: dict):
        logger.debug(f"Initializing {self.__class__.__name__} chat model")

        # Define the expected keys and their default values
        default_model_params = {
            "temperature": 0,
            "max_tokens": 4000,
            "top_p": 1,
            "top_k": 1
        }

        model_kwargs = self._process_model_params(settings, default_model_params)
        logger.info(
            f"Model {self.__class__.__name__} initializing with model parameters: {model_kwargs}"
        )

        llm_params = {
            "model_id": settings["MODEL_ID"],
            "service_endpoint": settings["OCI_GENAI_ENDPOINT"],
            "compartment_id": settings["OCI_COMPARTMENT_ID"],
            "auth_type": "API_KEY",
            "auth_profile": settings["OCI_CONFIG_PROFILE"],
            "model_kwargs": model_kwargs,
        }

        self._llm = ChatOCIGenAI(**llm_params)

    @property
    def llm(self):
        return self._llm
