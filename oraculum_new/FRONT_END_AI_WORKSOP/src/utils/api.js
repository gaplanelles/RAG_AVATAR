export const fetchData = async (endpoint, options = {}) => {
  const response = await fetch(endpoint, options);
  if (!response.ok) {
    throw new Error("Network response was not ok");
  }
  return response.json();
};
