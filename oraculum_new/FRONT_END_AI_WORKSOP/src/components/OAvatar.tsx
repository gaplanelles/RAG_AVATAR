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
import { isListeningButtonEnabled, isTalkingActive } from "../pages/ChatPage";
import { useVideo } from "../context/VideoContext";



const hygenApiKey = process.env.REACT_APP_HEYGEN_API_KEY;
const hygenApiUrl = process.env.REACT_APP_HEYGEN_API_URL;
const llmApiUrl = process.env.REACT_APP_LLM_API_URL;
const avatarName = process.env.REACT_APP_HEGYGEN_AVATAR_NAME;

const OAvatar: React.FC<{
  isVideoEnabled: boolean;
}> = ({ isVideoEnabled }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  // const [avatar, setAvatar] = useState<StreamingAvatar | null>(null);
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
    console.log("isListeningEnabled", isListeningButtonEnabled.value);
    avatar?.on(StreamingEvents.AVATAR_START_TALKING, () => {
      setIsVideoActive(true);
      console.log(
        "StreamingEvents.AVATAR_START_TALKING",
        isListeningButtonEnabled.value
      );
      if (isListeningButtonEnabled.value) {
        stopListening();
      }
    });
    avatar?.on(StreamingEvents.AVATAR_STOP_TALKING, () => {
      setIsVideoActive(false);
      console.log(
        "StreamingEvents.AVATAR_STOP_TALKING",
        isListeningButtonEnabled.value
      );
      if (isListeningButtonEnabled.value) {
        restartListening();
      }
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

  const initializeAvatarSession = async () => {
    try {
      setIsLoadingAvatar(true);
      // Ensure any previous instance is fully stopped before starting a new one
      if (avatar) {
        try {
          await avatar.stopAvatar();
        } catch (e) {
          // swallow unauthorized/invalid state errors
          // eslint-disable-next-line no-console
          console.warn("Stopping previous avatar before init failed (continuing)", e);
        }
        if (videoRef.current) {
          videoRef.current.srcObject = null;
        }
        setAvatar(null);
      }
      const token = await fetchAccessToken();
      if (!token) {
        console.error("HeyGen access token missing; aborting avatar start");
        setIsLoadingAvatar(false);
        return;
      }
      const newAvatar = new StreamingAvatar({ token });
      setAvatar(newAvatar);

      // Attach listeners BEFORE starting the avatar to avoid missing early events
      newAvatar.on(StreamingEvents.STREAM_READY, handleStreamReady);
      newAvatar.on(
        StreamingEvents.STREAM_DISCONNECTED,
        handleStreamDisconnected
      );

      const data = await newAvatar.createStartAvatar({
        quality: AvatarQuality.High,
        voice:   {
          //rate: 1.1, //spanish pure
          rate: 0.9,
          emotion : VoiceEmotion.FRIENDLY,
          //voiceId: "011af09cedd141feb57eafa51e5e98f9", //Serbian: 511ffd086a904ef593b608032004112c Spanish(multilingual): 011af09cedd141feb57eafa51e5e98f9, a78e0a4dbbe247d0a704b91175e6d987, Spanish (pure: a78e0a4dbbe247d0a704b91175e6d987)

        },
        avatarName: avatarName || "avatar",
        disableIdleTimeout: false
      });

      setSessionData(data);
      setIsSessionActive(true);
      setIsLoadingAvatar(false);
    } catch (error) {
      console.error("Error initializing avatar session:", error);
      setIsLoadingAvatar(false);
    }
  };

  const handleStreamReady = (event: any) => {
    if (event.detail && videoRef.current) {
      // If overlay was hiding the video, keep the element mounted to avoid detachment mid-play
      // Attach MediaStream and try to play
      videoRef.current.srcObject = event.detail;
      // Ensure autoplay policies don't block playback
      videoRef.current.autoplay = true;
      videoRef.current.playsInline = true;
      videoRef.current.muted = true; // allow autoplay on mobile/web
      videoRef.current.onloadedmetadata = () => {
        videoRef.current?.play().catch(console.error);
      };
      // Retry play shortly in case of race conditions
      setTimeout(() => {
        videoRef.current?.play().catch(() => {});
      }, 250);
      // Additional retry in case track arrives a bit later
      setTimeout(() => {
        videoRef.current?.play().catch(() => {});
      }, 750);
    }
  };

  const handleStreamDisconnected = () => {
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsSessionActive(false);
  };

  const terminateAvatarSession = async () => {
    if (avatar) {
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
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
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
                    autoPlay
                    muted
                    playsInline
                />
            </div>

        </LoadingOverlay>


  );
};

export default OAvatar;
