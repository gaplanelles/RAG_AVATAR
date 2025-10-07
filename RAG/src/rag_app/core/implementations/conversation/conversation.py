from typing import List
from ...interfaces.conversation_interface import ConversationInterface, Message

class Conversation(ConversationInterface):
    def __init__(self, initial_messages: List[Message] = None):
        self.history: List[Message] = initial_messages or []

    def add_message(self, role: str, content: str) -> None:
        self.history.append(Message(role=role, content=content))

    def get_history(self) -> List[Message]:
        return self.history

    def get_formatted_history(self) -> str:
        def translate_role(role: str) -> str:
            if role == "Assistant":
                return "Assistant"
            elif role == "User":
                return "Utilisateur"
            return role
        return "\n".join([f"{translate_role(msg.role)}: {msg.content}" for msg in self.history])

    def clear(self) -> None:
        self.history.clear()

    def get_last_n_messages_by_role(self, role: str, n: int) -> str:
        def translate_role(role: str) -> str:
            if role == "Assistant":
                return "Assistant"
            elif role == "User":
                return "Utilisateur"
            return role
        filtered_messages = [msg for msg in self.history if msg.role == role]
        last_n_messages = filtered_messages[-n:] if filtered_messages else []
        return "\n".join([f"{translate_role(msg.role)}: {msg.content}" for msg in last_n_messages]) or "No messages found."
