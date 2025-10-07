import React, { useRef, useState, useCallback, useEffect } from "react";
import Webcam from "react-webcam";
import '../styles/videoCam.css';

const videoConstraints = {
    width: 360,
    height: 180,
    facingMode: "user"
  };

  export const VideoCam = () => {
    const [isCaptureEnable, setCaptureEnable] = useState<boolean>(false);
    const webcamRef = useRef<Webcam>(null);
    const [url, setUrl] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [description, setDescription] = useState<string>('');
  
    const capture = useCallback(() => {
      const imageSrc = webcamRef.current?.getScreenshot();
      if (imageSrc) {
        setUrl(imageSrc);
      }
    }, [webcamRef]);
  
    const getDescription = async (imageBase64: string) => {
        try {
            const response = await fetch('http://139.185.59.9:9000/analyze_image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_base64: imageBase64 }),
            });
            const data = await response.json();
            setDescription(data.description || 'Error analyzing image');
        } catch (error) {
            console.error('Error sending image:', error);
            setDescription('Failed to analyze image.');
        }
    };
  
    useEffect(() => {
        const interval = setInterval(() => {
            const screenshot = webcamRef.current?.getScreenshot();
            if (screenshot) {
                getDescription(screenshot);
            }
        }, 3000);
  
        return () => clearInterval(interval);
    }, []);
  
    console.log("Rendering VideoCam component");
  
    return (
        <>
        <p className="video-title">¿Qué está viendo María?</p>
      <div className="video-container">
        
        <div className="webcam-wrapper">
          <Webcam
            audio={false}
            width={360}
            height={180}
            ref={webcamRef}
            screenshotFormat="image/jpeg"
            videoConstraints={videoConstraints}
            className="rounded-video"
            onUserMediaError={(err) => {
              console.error("Error accessing webcam:", err);
              setError("Error accessing webcam. Please check your camera settings.");
            }}
          />
          {error && <p style={{ color: 'red' }}>{error}</p>}
        </div>

        {url && (
          <>
            <div>
              <button
                onClick={() => {
                  setUrl(null);
                }}
              >
                delete
              </button>
            </div>
            <div>
              <img src={url} alt="Screenshot" />
            </div>
          </>
        )}
        
        <div className="description-box">
          <p>Description: {description}</p>
        </div>
      </div>
      </>
    );
  };
  
  export default VideoCam;

  //        <button onClick={capture}>capture</button>