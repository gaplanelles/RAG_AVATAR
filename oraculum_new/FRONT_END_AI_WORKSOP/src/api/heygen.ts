// api/heygen.js

export const HEYGEN_API_KEY =
  "MGNhY2E3MmZjMjVhNGMyNDhhNjIxYjZlNzQ4NGMyODEtMTczNDk0OTAxOA==";
// export const HEYGEN_API_URL = 'https://api.heygen.com/v1';
const HEYGEN_API_URL = "https://api.heygen.com/v1";

export const heygenApi = {
  // Inicjalizacja avatara
  createAvatar: async (avatarData: any): Promise<any> => {
    try {
      const response = await fetch(`${HEYGEN_API_URL}/streaming.new`, {
        method: "POST",
        headers: {
          'x-api-key': `${HEYGEN_API_KEY}`,
          "Content-Type": "application/json",
          "accept": "application/json",
        },
        body: JSON.stringify({
          quality: 'medium',
          voice: {rate: 0.8},
          video_encoding: 'VP8',
          disable_idle_timeout: false
        })
      });
      // const response = await fetch(`${HEYGEN_API_URL}/avatars`, {
      //   method: "POST",
      //   headers: {
      //     "x-api-key": `${HEYGEN_API_KEY}`,
      //     "Content-Type": "application/json",
      //     accept: "application/json",
      //   },
      //   body: JSON.stringify(avatarData),
      // });
      return await response.json();
    } catch (error) {
      console.error("Error creating avatar:", error);
      // throw error;
    }
  },

  // Rozpoczęcie streamingu
  startStream: async (avatarId: any, streamConfig: any) => {
    try {
      const response = await fetch(`${HEYGEN_API_URL}/stream/start`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${HEYGEN_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          avatar_id: avatarId,
          ...streamConfig,
        }),
      });
      return await response.json();
    } catch (error) {
      console.error("Error starting stream:", error);
      // throw error;
    }
  },

  // Zakończenie streamingu
  stopStream: async (streamId: any) => {
    try {
      const response = await fetch(
        `${HEYGEN_API_URL}/stream/${streamId}/stop`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${HEYGEN_API_KEY}`,
          },
        }
      );
      return await response.json();
    } catch (error) {
      console.error("Error stopping stream:", error);
      // throw error;
    }
  },

  // Wysyłanie tekstu do konwersji na mowę
  sendText: async (streamId: any, text: any) => {
    try {
      const response = await fetch(`${HEYGEN_API_URL}/stream/${streamId}/tts`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${HEYGEN_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text: text,
          voice_id: "default", // lub konkretne voice_id
        }),
      });
      return await response.json();
    } catch (error) {
      console.error("Error sending text:", error);
      // throw error;
    }
  },
};
