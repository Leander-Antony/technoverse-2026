import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import '../styles/ClaimDecision.css';

function ClaimDecision() {
  const { claimId } = useParams();
  const navigate = useNavigate();
  const [decision, setDecision] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('decision');

  useEffect(() => {
    const fetchDecisionData = async () => {
      try {
        // Fetch decision
        const decisionResponse = await fetch(
          `http://localhost:8000/api/v1/claims/${claimId}/decision`
        );
        if (!decisionResponse.ok) throw new Error('Failed to fetch decision');
        const decisionData = await decisionResponse.json();
        setDecision(decisionData);

        // Fetch explanation
        const explanationResponse = await fetch(
          `http://localhost:8000/api/v1/claims/${claimId}/explanation`
        );
        if (!explanationResponse.ok) throw new Error('Failed to fetch explanation');
        const explanationData = await explanationResponse.json();
        setExplanation(explanationData);

        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDecisionData();
  }, [claimId]);

  if (loading) {
    return (
      <div className="claim-decision">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading decision details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="claim-decision">
        <div className="error-container">
          <h2>⚠️ Error</h2>
          <p>{error}</p>
          <button className="btn btn-secondary" onClick={() => navigate('/')}>
            ← Back to Submit Claim
          </button>
        </div>
      </div>
    );
  }

  const getDecisionIcon = (decision) => {
    switch (decision) {
      case 'approved':
        return '✅';
      case 'rejected':
        return '❌';
      case 'manual_review':
        return '⚠️';
      default:
        return '📋';
    }
  };

  const getDecisionColor = (decision) => {
    switch (decision) {
      case 'approved':
        return '#4CAF50';
      case 'rejected':
        return '#f44336';
      case 'manual_review':
        return '#FF9800';
      default:
        return '#2196F3';
    }
  };

  return (
    <div className="claim-decision">
      <div className="decision-container">
        
        {/* Header */}
        <div className="decision-header">
          <h1>📄 Claim Decision</h1>
          <div className="claim-id-box">
            <span className="label">Claim ID:</span>
            <span className="claim-id">{claimId}</span>
          </div>
        </div>

        {/* Decision Banner */}
        {decision && (
          <div
            className={`decision-banner decision-${decision.decision}`}
            style={{ borderLeftColor: getDecisionColor(decision.decision) }}
          >
            <div className="banner-content">
              <span className="decision-icon">
                {getDecisionIcon(decision.decision)}
              </span>
              <div className="banner-text">
                <h2>{decision.decision.toUpperCase()}</h2>
                <p>
                  {decision.decision === 'approved'
                    ? `Approved Payout: ₹${decision.payout_amount.toLocaleString('en-IN')}`
                    : decision.decision === 'rejected'
                    ? 'This claim has been rejected'
                    : 'This claim requires manual review'}
                </p>
              </div>
              <div className="confidence-badge">
                <span className="label">Confidence</span>
                <span className="value">
                  {(decision.confidence_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'decision' ? 'active' : ''}`}
            onClick={() => setActiveTab('decision')}
          >
            📋 Decision
          </button>
          <button
            className={`tab ${activeTab === 'explanation' ? 'active' : ''}`}
            onClick={() => setActiveTab('explanation')}
          >
            📖 Full Explanation
          </button>
          <button
            className={`tab ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            🔍 Audit Trail
          </button>
        </div>

        {/* Tab Content */}
        <div className="tab-content">
          
          {/* Decision Tab */}
          {activeTab === 'decision' && decision && (
            <div className="decision-details">
              <div className="detail-section">
                <h3>Decision Summary</h3>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="label">Status:</span>
                    <span className={`value status-${decision.decision}`}>
                      {decision.decision.toUpperCase()}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Payout Amount:</span>
                    <span className="value payout">
                      ₹{decision.payout_amount.toLocaleString('en-IN')}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Confidence Score:</span>
                    <span className="value">
                      {(decision.confidence_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Decision Time:</span>
                    <span className="value">
                      {new Date(decision.decision_timestamp).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>

              <div className="detail-section">
                <h3>Decision Reasoning</h3>
                <div className="reasoning-box">
                  <pre>{decision.reasoning}</pre>
                </div>
              </div>

              {decision.decision_factors && (
                <div className="detail-section">
                  <h3>Decision Factors</h3>
                  <div className="factors-grid">
                    {Object.entries(decision.decision_factors).map(([key, value]) => (
                      <div key={key} className="factor-item">
                        <span className="factor-name">{key}:</span>
                        <span className="factor-value">
                          {typeof value === 'boolean'
                            ? value
                              ? '✓ Yes'
                              : '✗ No'
                            : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Explanation Tab */}
          {activeTab === 'explanation' && explanation && (
            <div className="explanation-content">
              <pre className="explanation-text">
                {explanation.explanation_text}
              </pre>

              <div className="detail-section">
                <h3>Policy Clauses Used</h3>
                <ul className="clauses-list">
                  {explanation.policy_clauses_used.map((clause, idx) => (
                    <li key={idx}>📋 {clause}</li>
                  ))}
                </ul>
              </div>

              <div className="detail-section">
                <h3>Damage Findings</h3>
                <div className="findings-box">
                  {Object.entries(explanation.damage_findings).map(([key, value]) => (
                    <div key={key} className="finding-item">
                      <span className="finding-key">{key}:</span>
                      <span className="finding-value">
                        {typeof value === 'object'
                          ? JSON.stringify(value)
                          : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {explanation.fraud_signals.length > 0 && (
                <div className="detail-section">
                  <h3>Fraud Risk Signals</h3>
                  <ul className="signals-list">
                    {explanation.fraud_signals.map((signal, idx) => (
                      <li key={idx}>🔐 {signal}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="compliance-badge">
                <span className="compliance-icon">✓</span>
                <span className="compliance-text">
                  {explanation.compliance_status}
                </span>
              </div>
            </div>
          )}

          {/* Audit Trail Tab */}
          {activeTab === 'audit' && explanation && (
            <div className="audit-content">
              <div className="audit-timeline">
                {explanation.audit_log.map((entry, idx) => (
                  <div key={idx} className="audit-entry">
                    <div className="audit-time">
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </div>
                    <div className="audit-marker"></div>
                    <div className="audit-details">
                      <div className="audit-agent">{entry.agent}</div>
                      <div className="audit-action">{entry.action}</div>
                      {Object.keys(entry.details).length > 0 && (
                        <div className="audit-info">
                          {Object.entries(entry.details).map(([key, value]) => (
                            <span key={key}>
                              {key}: {String(value)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="decision-actions">
          <button className="btn btn-secondary" onClick={() => navigate('/')}>
            ➕ File Another Claim
          </button>
          <button
            className="btn btn-primary"
            onClick={() => window.print()}
          >
            🖨️ Print Decision
          </button>
        </div>
      </div>
    </div>
  );
}

export default ClaimDecision;
