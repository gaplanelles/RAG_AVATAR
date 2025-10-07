import React from "react";
import { Link } from "react-router-dom";
import "../styles/Header.css";


const Header: React.FC = () => {
  return (
    <header className="app-header">
      <div className="header-content">
        <div className="header-left">
          <Link to="/" className="logo">
            <div className="header-logo-wrapper">
              <img
                src="https://upload.wikimedia.org/wikipedia/commons/5/50/Oracle_logo.svg"
                alt="Oracle"
                className="oracle-logo"
              />
            </div>
          </Link>
          <img
            src="/images/logo.png"
            alt="AION"
            className="aion-logo"
          />
        </div>
        <nav className="header-nav">
          <Link to="/" className="nav-link">Home</Link>
          <Link to="/setup" className="nav-link">Setup</Link>
          <Link to="/chat" className="nav-link">Chat</Link>
        </nav>
        <div className="header-right" />

      </div>
    </header>
  );
}

export default Header;