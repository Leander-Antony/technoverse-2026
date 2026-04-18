import React from 'react';
import '../styles/Navigation.css';
import { Link } from 'react-router-dom';

function Navigation() {
  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          <span className="logo-icon">⚡</span>
          ClaimFast
        </Link>
        
        <ul className="nav-menu">
          <li className="nav-item">
            <Link to="/" className="nav-link">
              📝 New Claim
            </Link>
          </li>
          <li className="nav-item">
            <a href="/api/docs" className="nav-link" target="_blank" rel="noopener noreferrer">
              📚 API Docs
            </a>
          </li>
          <li className="nav-item">
            <span className="nav-link status-badge">
              ✓ Online
            </span>
          </li>
        </ul>
      </div>
    </nav>
  );
}

export default Navigation;
