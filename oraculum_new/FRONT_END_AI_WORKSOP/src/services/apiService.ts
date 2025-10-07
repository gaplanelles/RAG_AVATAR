const hygenApiUrl = process.env.REACT_APP_HYGEN_API_URL;
const hygenApiKey = process.env.REACT_APP_HYGEN_API_KEY;

export const fetchAccessToken = async (): Promise<string> => {
  const response = await fetch(`${hygenApiUrl}/streaming.create_token`, {
    method: "POST",
    headers: {
      "x-api-key": hygenApiKey || "",
      "Content-Type": "application/json",
      "accept": "application/json",
    },
  });

  const { data } = await response.json();
  return data.token;
};