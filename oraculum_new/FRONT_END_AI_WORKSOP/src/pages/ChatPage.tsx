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
import VideoCam from "../components/videoCam";

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
  const [teamBlueSpeech, setTeamBlueSpeech] = useState("");
  const [teamWhiteSpeech, setTeamWhiteSpeech] = useState("");
  const [isTeamBlueListening, setIsTeamBlueListening] = useState(false);
  const [isTeamWhiteListening, setIsTeamWhiteListening] = useState(false);
  const [isStructuringBlue, setIsStructuringBlue] = useState(false);
  const [isStructuringWhite, setIsStructuringWhite] = useState(false);
  const [isTeamSpeechCollapsed, setIsTeamSpeechCollapsed] = useState(true);
  const chatBoxRef = useRef<any>(null);
  const dataFetchedRef = useRef(false);
  const recognitionRef = useRef<any>(null);

  // Queue to hold incoming tokens
  const tokenQueueRef = useRef<string[]>([]);
  // Flag to indicate if processing is ongoing
  const isProcessingRef = useRef(false);
  // Minimum delay between tokens in milliseconds
  const MIN_DELAY = 30; // Adjust as needed

  const [showSatelliteIcon, setShowSatelliteIcon] = useState(false);
  const [isCameraVisible, setIsCameraVisible] = useState(false);

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
          setShowSatelliteIcon(true);
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

  const handleRobotButtonClick = async () => {
    if (isVideoEnabled && avatar?.mediaStream) {
      try {
        await avatar.interrupt();
      } catch (error) {
        if (error instanceof Error && 'code' in error && (error as any).code === 400112) {
          console.warn("Unauthorized error while interrupting avatar, continuing...");
        } else {
          console.error("Error interrupting avatar:", error);
        }
      }
      toggleVideo();
    } else {
      toggleVideo();
    }
  };

  const restartVideoAndAvatar = async () => {
    try {
      console.log("Closing connections...");

      // Stop the avatar if it's active
      if (avatar) {
        try {
          await avatar.stopAvatar();
        } catch (error) {
          if (error instanceof Error && 'code' in error && (error as any).code === 400112) {
            console.warn("Unauthorized error while stopping avatar, continuing...");
          } else {
            console.error("Error stopping avatar:", error);
          }
        }
        setAvatar(null);
      }

      // Ensure video is disabled
      if (isVideoEnabled) {
        toggleVideo(); // This will set isVideoEnabled to false
      }

      // Set video active state to false
      setIsVideoActive(false);

      console.log("Connections closed successfully.");
      setShowSatelliteIcon(false);

      // Call the robot button click handler
      await handleRobotButtonClick();

    } catch (error) {
      console.error("Error closing connections:", error);
    }
  };

  const handleStreamReady = (event: any) => {
    if (event.detail && chatBoxRef.current) {
      chatBoxRef.current.srcObject = event.detail;
      chatBoxRef.current.onloadedmetadata = () => {
        chatBoxRef.current?.play().catch(console.error);
      };
    }
    setIsVideoActive(true);
  };

  const handleStreamDisconnected = () => {
    if (chatBoxRef.current) {
      chatBoxRef.current.srcObject = null;
    }
    setIsVideoActive(false);
  };

  const toggleCameraVisibility = () => {
    setIsCameraVisible(!isCameraVisible);
  };

  useEffect(() => {
    // Initialize speech recognition
    if ('webkitSpeechRecognition' in window) {
      recognitionRef.current = new (window as any).webkitSpeechRecognition();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';
    }
  }, []);

  const startTeamBlueListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((result: any) => result[0].transcript)
          .join('');
        setTeamBlueSpeech(transcript);
      };
      recognitionRef.current.start();
      setIsTeamBlueListening(true);
    }
  };

  const stopTeamBlueListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsTeamBlueListening(false);
    }
  };

  const startTeamWhiteListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((result: any) => result[0].transcript)
          .join('');
        setTeamWhiteSpeech(transcript);
      };
      recognitionRef.current.start();
      setIsTeamWhiteListening(true);
    }
  };

  const stopTeamWhiteListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsTeamWhiteListening(false);
    }
  };

  const toggleTeamBlueListening = () => {
    if (isTeamBlueListening) {
      stopTeamBlueListening();
    } else {
      // Stop white team if it's listening
      if (isTeamWhiteListening) {
        stopTeamWhiteListening();
      }
      startTeamBlueListening();
    }
  };

  const toggleTeamWhiteListening = () => {
    if (isTeamWhiteListening) {
      stopTeamWhiteListening();
    } else {
      // Stop blue team if it's listening
      if (isTeamBlueListening) {
        stopTeamBlueListening();
      }
      startTeamWhiteListening();
    }
  };

  const structureText = async (text: string, isBlue: boolean) => {
    try {
      if (isBlue) {
        setIsStructuringBlue(true);
      } else {
        setIsStructuringWhite(true);
      }

      const response = await fetch(API_ENDPOINTS.STRUCTURING_SPEECH, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        throw new Error('Failed to structure text');
      }

      const data = await response.json();
      
      if (isBlue) {
        setTeamBlueSpeech(data.structured_speech || '');
      } else {
        setTeamWhiteSpeech(data.structured_speech || '');
      }
    } catch (error) {
      console.error('Error structuring text:', error);
      // You might want to show an error message to the user here
    } finally {
      if (isBlue) {
        setIsStructuringBlue(false);
      } else {
        setIsStructuringWhite(false);
      }
    }
  };

  const mergeSpeeches = () => {
    if (teamBlueSpeech && teamWhiteSpeech) {
      const mergedText = `**Team Blue Speech:**\n\n${teamBlueSpeech}\n\n**Team White Speech:**\n\n${teamWhiteSpeech}`;
      
      // Add the merged text as a user message
      const newMessage = { type: "user", content: mergedText };
      setMessages((prevMessages: any) => [
        ...prevMessages,
        newMessage,
        { type: "system", content: "" },
      ]);

      // Send the merged text to the chat
      fetchResponse(
        mergedText,
        messages,
        setMessages,
        handleStreamResponse
      );

      // Clear both text areas
      setTeamBlueSpeech("");
      setTeamWhiteSpeech("");
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
            <div className="chat-interface">
              <div className="container">
                <div className="mb-3 d-flex justify-content-between">
                  <div />
                  <div>AION Chat</div>
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
                    <div
                      onClick={() => setIsTeamSpeechCollapsed(!isTeamSpeechCollapsed)}
                      className="me-2"
                      role="button"
                    >
                      <i className={`fas fa-lg fa-comments ${isTeamSpeechCollapsed ? "text-secondary text-warning-hover" : "text-warning text-secondary-hover"}`} />
                    </div>

                    <div
                      onClick={restartVideoAndAvatar}
                      className="me-2"
                      role="button"
                    >
                      <i className="fas fa-lg fa-satellite text-secondary text-warning-hover" />
                    </div>
                    
                    <div
                      onClick={handleRobotButtonClick}
                      className="me-2"
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
                  <div>Mary - Your virtual assistant</div>
                  <div />
                </div>
                <OAvatar isVideoEnabled={isVideoEnabled} />
                <br />
                <div className="d-flex justify-content-center mb-3">
                  <div
                    onClick={toggleCameraVisibility}
                    className="btn btn-link"
                    role="button"
                  >
                    <i className={`fas fa-eye${isCameraVisible ? '' : '-slash'} text-secondary text-warning-hover`} />
                  </div>
                </div>
                {isCameraVisible && <VideoCam />}
                
                
                
               

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

          <div className={`team-speech-container ${isTeamSpeechCollapsed ? "collapsed" : ""}`}>
            
            <div className="team-speech-section">
              <h3>Team Blue Speech</h3>
              <div className="team-speech-input">
                <div className="team-speech-content">
                  <textarea
                    value={teamBlueSpeech}
                    onChange={(e) => setTeamBlueSpeech(e.target.value)}
                    placeholder="Team Blue's speech will appear here..."
                    className="team-speech-textarea"
                  />
                  <div className="team-speech-controls">
                    <div 
                      className="team-speech-mic"
                      onClick={toggleTeamBlueListening}
                    >
                      <i
                        className={`fas fa-lg fa-microphone ${
                          isTeamBlueListening
                            ? "text-warning text-secondary-hover"
                            : "text-secondary text-warning-hover"
                        }`}
                        role="button"
                      />
                    </div>
                    <button
                      className={`structure-button ${isStructuringBlue ? 'loading' : ''}`}
                      onClick={() => structureText(teamBlueSpeech, true)}
                      disabled={!teamBlueSpeech || isStructuringBlue}
                      title="Structure text using AI"
                    >
                      <i className="fas fa-magic" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div className="team-speech-section">
              <h3>Team White Speech</h3>
              <div className="team-speech-input">
                <div className="team-speech-content">
                  <textarea
                    value={teamWhiteSpeech}
                    onChange={(e) => setTeamWhiteSpeech(e.target.value)}
                    placeholder="Team White's speech will appear here..."
                    className="team-speech-textarea"
                  />
                  <div className="team-speech-controls">
                    <div 
                      className="team-speech-mic"
                      onClick={toggleTeamWhiteListening}
                    >
                      <i
                        className={`fas fa-lg fa-microphone ${
                          isTeamWhiteListening
                            ? "text-warning text-secondary-hover"
                            : "text-secondary text-warning-hover"
                        }`}
                        role="button"
                      />
                    </div>
                    <button
                      className={`structure-button ${isStructuringWhite ? 'loading' : ''}`}
                      onClick={() => structureText(teamWhiteSpeech, false)}
                      disabled={!teamWhiteSpeech || isStructuringWhite}
                      title="Structure text using AI"
                    >
                      <i className="fas fa-magic" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div className="merge-speeches-container">
              <button
                className="merge-button"
                onClick={mergeSpeeches}
                disabled={!teamBlueSpeech || !teamWhiteSpeech}
              >
                Merge Speeches
              </button>
            </div>
          </div>

        </div>
      </div>

    </>
  );
}

export default ChatPage;


// <VideoCam /> On line 494, after <br> <br>
