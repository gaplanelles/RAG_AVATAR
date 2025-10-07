import "../styles/OAvatar.css";
import React, { useEffect, useRef, useState } from "react";
import StreamingAvatar, {
  AvatarQuality,
  StreamingEvents,
  TaskMode,
  TaskType,
  VoiceEmotion,
} from "@heygen/streaming-avatar";
import LoadingOverlay from "./LoadingOverlay";
import { useTranscription } from "../context/TranscriptionContext";
import { isListeningButtonEnabled } from "../pages/ChatPage";
import { useVideo } from "../context/VideoContext";

const hygenApiKey = process.env.REACT_APP_HEYGEN_API_KEY;
const hygenApiUrl = process.env.REACT_APP_HEYGEN_API_URL;
const llmApiUrl = process.env.REACT_APP_LLM_API_URL;
const avatarName = process.env.REACT_APP_HEGYGEN_AVATAR_NAME;

const OAvatar: React.FC<{ isVideoEnabled: boolean }> = ({ isVideoEnabled }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [sessionData, setSessionData] = useState<any>(null);
  const [lastReadText, setLastReadText] = useState("");
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [isLoadingAvatar, setIsLoadingAvatar] = useState(false);
  const { stopListening, restartListening } = useTranscription();
  const { avatar, setAvatar, setIsVideoActive } = useVideo();

  useEffect(() => {
    if (isVideoEnabled) {
      initializeAvatarSession();
    } else {
      terminateAvatarSession();
    }
  }, [isVideoEnabled]);

  useEffect(() => {
    avatar?.on(StreamingEvents.AVATAR_START_TALKING, () => {
      setIsVideoActive(true);
      if (isListeningButtonEnabled.value) stopListening();
    });
    avatar?.on(StreamingEvents.AVATAR_STOP_TALKING, () => {
      setIsVideoActive(false);
      if (isListeningButtonEnabled.value) restartListening();
    });
  }, [avatar]);

  const fetchAccessToken = async (): Promise<string> => {
    try {
      const response = await fetch(`${hygenApiUrl}/streaming.create_token`, {
        method: "POST",
        headers: {
          "x-api-key": hygenApiKey || "",
          "Content-Type": "application/json",
          accept: "application/json",
        },
      });
      const { data } = await response.json();
      return data.token;
    } catch (e) {
      setIsLoadingAvatar(false);
      return "";
    }
  };

  const fetchResponseLanguage = async (): Promise<string> => {
    try {
      const response = await fetch("https://139.185.59.9:9007/get_response_language");
      const data = await response.json();
      return data.value;
    } catch (error) {
      console.error("Error fetching response language:", error);
      return "";
    }
  };

  const initializeAvatarSession = async () => {
    try {
      setIsLoadingAvatar(true);

      const token = await fetchAccessToken();
      const responseLanguage = await fetchResponseLanguage();

      const voiceId =
        responseLanguage.trim() === "Español."
          ? "a78e0a4dbbe247d0a704b91175e6d987"
          : "011af09cedd141feb57eafa51e5e98f9";

      const newAvatar = new StreamingAvatar({ token });
      setAvatar(newAvatar);

      const data = await newAvatar.createStartAvatar({
        quality: AvatarQuality.High,
        voice: {
          rate: 0.9,
          emotion: VoiceEmotion.FRIENDLY,
          voiceId: voiceId,
        },
        avatarName: avatarName || "avatar",
        disableIdleTimeout: false,
      });

      setSessionData(data);
      setIsSessionActive(true);

      newAvatar.on(StreamingEvents.STREAM_READY, handleStreamReady);
      newAvatar.on(StreamingEvents.STREAM_DISCONNECTED, handleStreamDisconnected);

      setIsLoadingAvatar(false);
    } catch (error) {
      console.error("Error initializing avatar session:", error);
      setIsLoadingAvatar(false);
    }
  };

  const handleStreamReady = (event: any) => {
    if (event.detail && videoRef.current) {
      videoRef.current.srcObject = event.detail;
      videoRef.current.onloadedmetadata = () => {
        videoRef.current?.play().catch(console.error);
      };
    }
  };

  const handleStreamDisconnected = () => {
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsSessionActive(false);
  };

  const terminateAvatarSession = async () => {
    if (avatar && sessionData && isSessionActive) {
      try {
        await avatar.stopAvatar();
        if (videoRef.current) {
          videoRef.current.srcObject = null;
        }
        setAvatar(null);
        setIsSessionActive(false);
      } catch (error) {
        console.error("Error terminating avatar session:", error);
      }
    }
  };

  const fetchAndReadText = async () => {
    try {
      const response = await fetch(`${llmApiUrl}/get_string`);
      const data = await response.json();
      console.log("data");
      console.log(data);
      const newText = data.response;

      if (newText !== lastReadText && avatar) {
        setLastReadText(newText);
        await avatar.speak({
          text: newText,
          task_type: TaskType.REPEAT,
          taskMode: TaskMode.SYNC,
        });
      }
    } catch (error) {
      console.error("Error fetching text:", error);
    }
  };

  useEffect(() => {
    let pollingInterval: any;
    if (isSessionActive) {
      fetchAndReadText();
      pollingInterval = setInterval(fetchAndReadText, 3000);
    }
    return () => {
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, [isSessionActive, avatar, lastReadText]);

  useEffect(() => {
    return () => {
      try {
        if (avatar) {
          avatar.stopAvatar().then(() => {}, console.error).catch(console.error);
          setAvatar(null);
          setIsSessionActive(false);
          setIsVideoActive(false);
        }
      } catch (error) {
        console.error("Error stopping avatar:", error);
      }
    };
  }, [avatar]);

  return (
    <LoadingOverlay isLoading={isLoadingAvatar}>
      <div className="avatar-container">
        <video
          ref={videoRef}
          id="avatarVideo"
          className="avatar-video"
          controls={true}
          playsInline
        />
      </div>
    </LoadingOverlay>
  );
};

export default OAvatar;
