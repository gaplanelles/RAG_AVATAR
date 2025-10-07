import StreamingAvatar from '@heygen/streaming-avatar';
import React, { createContext, useContext, useState } from 'react';

interface VideoContextProps {
  isVideoEnabled: boolean;
  isVideoActive: boolean;
  toggleVideo: () => void;
  setIsVideoActive: (flag: boolean) => void;
  avatar: StreamingAvatar | null;
  setAvatar: (avatar: StreamingAvatar | null) => void;
}

const VideoContext = createContext<VideoContextProps | undefined>(undefined);

interface VideoProviderProps {
  children: React.ReactNode;
}

export const VideoProvider: React.FC<VideoProviderProps> = ({ children }) => {
  const [avatar, setAvatar] = useState<StreamingAvatar | null>(null);
  const [isVideoEnabled, setIsVideoEnabled] = useState(false);
  const [isVideoActive, setIsVideoActive] = useState(false);

  const toggleVideo = () => {
    setIsVideoEnabled((prev) => !prev);
  };

  return (
    <VideoContext.Provider value={{ avatar, setAvatar, isVideoEnabled, toggleVideo, isVideoActive, setIsVideoActive }}>
      {children}
    </VideoContext.Provider>
  );
};

export const useVideo = () => {
  const context = useContext(VideoContext);
  if (!context) {
    throw new Error('useVideo must be used within a VideoProvider');
  }
  return context;
};