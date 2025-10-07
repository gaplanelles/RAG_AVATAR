import { API_ENDPOINTS } from "../config/apiConfig";
import { createParser } from "eventsource-parser";

export const fetchData = async (url: string) => {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return await response.json();
};

export const cleanConversation = async () => {
  try {
    const response = await fetch(API_ENDPOINTS.CLEAN_CONVERSATION, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error("Failed to clean conversation");
    }
  } catch (error) {
    console.error(`${new Date().toISOString()} - Error cleaning conversation:`, error);
    // throw error;
  }
};

export const fetchInitialResponse = async (setMessages: any, handleStreamResponse: any) => {
  const url = API_ENDPOINTS.INIT;
  const data = {
    message: "how are you?",
    genModel: "OCI_CommandRplus",
    conversation: [],
  };

  console.log(`${new Date().toISOString()} - Sending initial request to:`, url);

  setMessages([{ type: "system", content: "" }]);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    await handleStreamResponse(response);
  } catch (error) {
    console.error(`${new Date().toISOString()} - Fetch error:`, error);
    setMessages((prevMessages: any) => {
      const newMessages = [...prevMessages];
      const lastMessage: any = newMessages[newMessages.length - 1];
      if (lastMessage && lastMessage.type === "system") {
        lastMessage.content = "Error: Failed to get initial response from the server.";
      }
      return newMessages;
    });
  }
};

export const fetchResponse = async (message: string, messages: any, setMessages: any, handleStreamResponse: any) => {
  const url = API_ENDPOINTS.ASK;
  const conversationHistory = formatConversationHistory(messages);

  const data = {
    message: message,
    genModel: "OCI_CommandRplus",
    conversation: conversationHistory,
  };

  console.log(`${new Date().toISOString()} - Sending request to:`, url);
  console.log("Conversation history:", conversationHistory);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    await handleStreamResponse(response);
  } catch (error) {
    console.error(`${new Date().toISOString()} - Fetch error:`, error);
    setMessages((prevMessages: any) => {
      const newMessages = [...prevMessages];
      const lastMessage: any = newMessages[newMessages.length - 1];
      if (lastMessage && lastMessage.type === "system") {
        lastMessage.content = "Error: Failed to get response from the server.";
      }
      return newMessages;
    });
  }
};

const formatConversationHistory = (messages: any) => {
  return messages
    .filter((msg: any) => msg.content.trim() !== "")
    .map((msg: any) => ({
      role: msg.type === "user" ? "User" : "Assistant",
      content: msg.content,
    }));
};

export const handleStreamResponse = async (response: any, onParse: any) => {
  const parser = createParser(onParse);
  const reader = response.body.getReader();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = new TextDecoder().decode(value);
      console.log(`${new Date().toISOString()} - Received chunk:`, chunk);
      parser.feed(chunk);
    }
  } catch (error) {
    console.error(`${new Date().toISOString()} - Error reading stream:`, error);
    // throw error;
  }
};