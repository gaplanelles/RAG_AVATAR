import React, { useState, useEffect, useRef, useCallback } from "react";
import { signal } from "@preact/signals-react";
import "../styles/ChatPage.css";
import RAGConfigDisplay from "../components/RAGConfigDisplay";
import SourceTabs from "../components/SourceTabs";
import { API_ENDPOINTS } from "../config/apiConfig";
import { createParser } from "eventsource-parser";
import OAvatar from "../components/OAvatar";
import { useVideo } from "../context/VideoContext";
import { useTranscription } from "../context/TranscriptionContext";
import {
  cleanConversation,
  fetchData,
  fetchInitialResponse,
  fetchResponse,
} from "../services/chatService";
import { TaskMode, TaskType } from "@heygen/streaming-avatar";
import ReactMarkdown from 'react-markdown';
import StreamingAvatar, { AvatarQuality, VoiceEmotion, StreamingEvents } from "@heygen/streaming-avatar";

export const isListeningButtonEnabled = signal(false);
export const isTalkingActive = signal(false);

function ChatPage() {
  const [messages, setMessages] = useState<any>([]);
  const { transcription, setTranscription } = useTranscription();
  const [isLoadingAnswer, setIsLoadingAnswer] = useState(false);
  const [configData, setConfigData] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [error, setError] = useState<string | null>(null);
  const [sources, setSources] = useState([]);
  const chatBoxRef = useRef<any>(null);
  const dataFetchedRef = useRef(false);

  // Queue to hold incoming tokens
  const tokenQueueRef = useRef<string[]>([]);
  // Flag to indicate if processing is ongoing
  const isProcessingRef = useRef(false);
  // Minimum delay between tokens in milliseconds
  const MIN_DELAY = 30; // Adjust as needed

  useEffect(() => {
    if (dataFetchedRef.current) return;
    dataFetchedRef.current = true;

    const fetchAllData = async () => {
      try {
        const [config, template] = await Promise.all([
          fetchData(API_ENDPOINTS.RAG_CONFIG),
          fetchData(API_ENDPOINTS.SETUP_RAG_TEMPLATE),
        ]);
        setConfigData(config);
        setMetadata(template.metadata);

        // Clean conversation before initializing
        await cleanConversation();
        await fetchInitialResponse(setMessages, handleStreamResponse);
      } catch (error) {
        console.error("Error fetching data:", error);
        setError("Failed to fetch data.");
      }
    };
    fetchAllData();
  }, []);

  const handleStreamResponse = async (response: any) => {
    const parser = createParser(onParse);
    const reader = response.body.getReader();
    setIsLoadingAnswer(true);
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = new TextDecoder().decode(value);
        // console.log(`${new Date().toISOString()} - Received chunk:`, chunk);
        parser.feed(chunk);
      }
    } catch (error) {
      console.error(
        `${new Date().toISOString()} - Error reading stream:`,
        error
      );
      updateLastMessage(
        (prevContent: any) =>
          prevContent + "\nError: Failed to read the response stream."
      );
    }
    setIsLoadingAnswer(false);
  };

  const onParse = (event: any) => {
    if (event.type === "event") {
      try {
        const data: any = JSON.parse(event.data);
        // console.log(`${new Date().toISOString()} - Parsed event:`, data);

        if (data.type === "content") {
          tokenQueueRef.current.push(data.content);
          processQueue();
        } else if (data.type === "done") {
          console.log(
            `${new Date().toISOString()} - Received 'done' message:`,
            data
          );
          handleDoneMessage(data);
        } else {
          console.log(
            `${new Date().toISOString()} - Unhandled message type:`,
            data.type
          );
        }
      } catch (error) {
        console.error(
          `${new Date().toISOString()} - Error parsing JSON:`,
          error
        );
      }
    }
  };

  const handleDoneMessage = (data: any) => {
    if (data.sources && Array.isArray(data.sources)) {
      // console.log("Sources received:", data.sources);
      setSources(data.sources);
    } else {
      console.log("No sources received or invalid format");
    }
  };

  const processQueue = useCallback(() => {
    if (isProcessingRef.current) return;
    isProcessingRef.current = true;

    const processNext = () => {
      if (tokenQueueRef.current.length === 0) {
        isProcessingRef.current = false;
        return;
      }

      const nextToken = tokenQueueRef.current.shift();
      updateLastMessage((prevContent: any) => prevContent + nextToken);
      // console.log(`${new Date().toISOString()} - Appended content:`, nextToken);

      setTimeout(processNext, MIN_DELAY);
    };

    processNext();
  }, []);

  const updateLastMessage = (updateFunction: any) => {
    setMessages((prevMessages: any) => {
      const newMessages = [...prevMessages];
      const lastMessage: any = newMessages[newMessages.length - 1];
      if (lastMessage && lastMessage.type === "system") {
        lastMessage.content =
          typeof updateFunction === "function"
            ? updateFunction(lastMessage.content)
            : updateFunction;
      } else {
        // If there's no system message, add one
        newMessages.push({
          type: "system",
          content:
            typeof updateFunction === "function"
              ? updateFunction("")
              : updateFunction,
        });
      }
      return newMessages;
    });
  };

  const sendMessage = async () => {
    if (transcription.trim()) {
      const newMessage = { type: "user", content: transcription.trim() };
      setMessages((prevMessages: any) => [
        ...prevMessages,
        newMessage,
        { type: "system", content: "" },
      ]);
      setTranscription("");
      await fetchResponse(
        newMessage.content,
        messages,
        setMessages,
        handleStreamResponse
      );
    }
  };

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  const scrollToBottom = () => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const {
    avatar,
    setAvatar,
    isVideoEnabled,
    toggleVideo,
    isVideoActive,
    setIsVideoActive,
  } = useVideo();
  const { startListening, stopListening, setIsListening } = useTranscription();

  useEffect(() => {
    if (!isVideoEnabled) {
      setIsVideoActive(false);
    }
  }, [isVideoEnabled]);

  const toggleListeningEnabled = () => {
    if (isListeningButtonEnabled.value) {
      isListeningButtonEnabled.value = false;
      setIsListening(false);
      stopListening();
    } else {
      isListeningButtonEnabled.value = true;
      setIsListening(true);
      startListening();
    }
  };

  async function speakingByAvatar(content: any) {
    if (avatar) {
      try {
        await avatar.speak({
          text: content,
          task_type: TaskType.REPEAT,
          taskMode: TaskMode.SYNC,
        });
      } catch (error: any) {
        console.error("Avatar speaking error:", error);
        if (error.message?.includes("401")) {
          console.log("Please refresh avatar by clicking on robot button");
          alert("Please refresh avatar by clicking on robot button");
        }
      }
    } else {
      console.warn("Avatar is not available to speak.");
    }
  }

  const renderMessageContent = (content: string) => {
    // Simple custom parser for basic markdown-like formatting
    const formattedContent = content
      .replace(/## (.+)/g, '<h2>$1</h2>') // Convert ## headers to <h2>
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>') // Convert **bold** to <strong>
      .replace(/- (.+)/g, '<li>$1</li>') // Convert list items
      .replace(/(?:\r\n|\r|\n)/g, '<br>'); // Convert new lines to <br>
    
    return { __html: `<ul>${formattedContent}</ul>` };
  };

  const fetchAccessToken = async (): Promise<string> => {
    try {
      console.log("Heygen API KEY")
      console.log(process.env.REACT_APP_HEYGEN_API_KEY)
      const response = await fetch(`${process.env.REACT_APP_HEYGEN_API_URL}/streaming.create_token`, {
        method: "POST",
        headers: {
          "x-api-key": process.env.REACT_APP_HEYGEN_API_KEY || "",
          "Content-Type": "application/json",
          accept: "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch access token");
      }

      const { data } = await response.json();
      return data.token;
    } catch (error) {
      console.error("Error fetching access token:", error);
      throw error;
    }
  };

  const avatarName = process.env.REACT_APP_HEGYGEN_AVATAR_NAME;

  const handleStreamReady = (event: any) => {
    if (event.detail && chatBoxRef.current) {
      chatBoxRef.current.srcObject = event.detail;
      chatBoxRef.current.onloadedmetadata = () => {
        chatBoxRef.current?.play().catch(console.error);
      };
    }
  };

  const handleStreamDisconnected = () => {
    if (chatBoxRef.current) {
      chatBoxRef.current.srcObject = null;
    }
    setIsVideoActive(false);
  };

  const restartVideoAndAvatar = async () => {
    try {
      // Stop the avatar if it's active
      if (avatar) {
        await avatar.stopAvatar();
        setAvatar(null);
      }

      // Disable video if it's enabled
      if (isVideoEnabled) {
        toggleVideo(); // This will set isVideoEnabled to false
      }

      // Reinitialize the avatar session
      const token = await fetchAccessToken();
      const newAvatar = new StreamingAvatar({ token });
      setAvatar(newAvatar);

      const data = await newAvatar.createStartAvatar({
        quality: AvatarQuality.High,
        voice: {
          rate: 0.8,
          emotion: VoiceEmotion.FRIENDLY,
        },
        avatarName: avatarName || "avatar",
        disableIdleTimeout: true,
      });

      // Enable video
      toggleVideo(); // This will set isVideoEnabled to true
      setIsVideoActive(true);

      // Handle stream events
      newAvatar.on(StreamingEvents.STREAM_READY, handleStreamReady);
      newAvatar.on(StreamingEvents.STREAM_DISCONNECTED, handleStreamDisconnected);

    } catch (error) {
      console.error("Error restarting video and avatar:", error);
    }
  };

  return (
    <>
      <div className="slide-container">
        <div
          id="leftContent"
          className={`left-content ${isVideoEnabled ? "slide-left" : ""}`}
        >
          <div className="chat-page-container pe-0">
            {/* isListening: {JSON.stringify(isListening)}
            <br />
            isListeningButtonEnabled.value: {JSON.stringify(isListeningButtonEnabled.value)}
            <br /> */}
            <div className="chat-interface">
              <div className="container">
                <div className="mb-3 d-flex justify-content-between">
                  <div />
                  <div>AI Chat</div>
                  <div className="d-flex">
                    {isVideoActive && (
                      <div
                        className="me-3"
                        onClick={() => {
                          setIsVideoActive(false);
                          if (avatar?.mediaStream) {
                            try {
                              avatar?.interrupt();
                            } catch (e) {
                              console.log(e);
                            }
                          }
                        }}
                      >
                        <i
                          className={`fas fa-lg fa-circle-stop text-warning text-secondary-hover`}
                          role="button"
                        />
                      </div>
                    )}
                    <button
                      onClick={restartVideoAndAvatar}
                      className="ms-2 btn btn-secondary"
                    >
                      Restart
                    </button>
                    <div
                      onClick={async () => {
                        if (isVideoEnabled && avatar?.mediaStream) {
                          avatar?.interrupt().then(
                            () => {
                              toggleVideo();
                            },
                            () => {}
                          );
                        } else {
                          toggleVideo();
                        }
                      }}
                    >
                      <i
                        className={`fas fa-lg fa-robot  ${
                          isVideoEnabled
                            ? "text-warning text-secondary-hover"
                            : "text-secondary text-warning-hover"
                        } `}
                        role="button"
                      />
                    </div>

                  </div>
                </div>
                <div id="chatBox" ref={chatBoxRef}>
                  {messages.map((msg: any, index: number) => (
                    <div key={index} className={`message ${msg.type}-message`}>
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                      {msg?.type === "system" &&
                        isVideoEnabled &&
                        avatar &&
                        !!msg?.content?.length && (
                          <div
                            className="text-end"
                            role="button"
                            onClick={() => {
                              speakingByAvatar(msg.content);
                            }}
                          >
                            <i className="fas fa-play text-secondary text-warning-hover text-right" />
                          </div>
                        )}
                    </div>
                  ))}
                </div>
                <div className="input-area d-flex align-items-center">
                  <input
                    type="text"
                    id="userInput"
                    disabled={isLoadingAnswer}
                    placeholder="Send a message..."
                    value={transcription}
                    onChange={(e) => setTranscription(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && sendMessage()}
                  />

                  <button
                    id="sendButton"
                    className="me-4"
                    disabled={isLoadingAnswer}
                    onClick={sendMessage}
                  >
                    <i className="fas fa-paper-plane"></i>
                  </button>
                  <div className="ms-2" onClick={toggleListeningEnabled}>
                    <i
                      className={`fas fa-lg fa-microphone ${
                        isListeningButtonEnabled.value
                          ? "text-warning text-secondary-hover"
                          : "text-secondary text-warning-hover"
                      } `}
                      role="button"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div
          id="hiddenContent"
          className={`hidden-content  ${isVideoEnabled ? "show-right" : ""}`}
        >
          <div className=" chat-page-container ps-0">
            <div className="chat-interface">
              <div className="container ">
                <div className="mb-3 d-flex d-flex justify-content-between">
                  <div />
                  <div>Mary - Your Virtual Assistant</div>
                  <div />
                </div>
                <OAvatar isVideoEnabled={isVideoEnabled} />
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="d-flex justify-content-center">
        <div className="bottom-section">
          <aside className="sidebar">
            <RAGConfigDisplay
              configData={configData}
              metadata={metadata}
              error={error}
            />
          </aside>
          <div className="sources-display">
            <div className="sources-header pb-2">
              <h3 className="mb-1">Sources</h3>
            </div>
            <div className="sources-content">
              <SourceTabs sources={sources} />
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default ChatPage;
