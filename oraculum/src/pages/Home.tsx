import React from "react";
import { Link } from "react-router-dom";
import "../styles/Home.css"; // Optional: Add styles for the Home component

const Home: React.FC = () => {
  return (
    <main className="home-container">
      <h2>Welcome to the RAG Application</h2>
      <p>Select a page to navigate:</p>
      <div className="links">
        <Link to="/setup" className="link-button">Go to Setup Page</Link>
        <Link to="/chat" className="link-button">Go to Chat Page</Link>
      </div>
    </main>
  );
}

export default Home;