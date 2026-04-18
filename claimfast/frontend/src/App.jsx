import React from 'react';
import './styles/App.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ClaimSubmission from './pages/ClaimSubmission';
import ClaimStatus from './pages/ClaimStatus';
import ClaimDecision from './pages/ClaimDecision';
import Navigation from './components/Navigation';

function App() {
  return (
    <Router>
      <div className="app-container">
        <Navigation />
        
        <main className="main-content">
          <Routes>
            <Route path="/" element={<ClaimSubmission />} />
            <Route path="/claim/:claimId/status" element={<ClaimStatus />} />
            <Route path="/claim/:claimId/decision" element={<ClaimDecision />} />
          </Routes>
        </main>

        <footer className="app-footer">
          <p>ClaimFast © 2024 | FNOL Insurance System | IRDAI Compliant</p>
        </footer>
      </div>
    </Router>
  );
}

export default App;
