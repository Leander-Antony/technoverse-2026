import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import '../styles/ClaimStatus.css';
import ProcessingStages from '../components/ProcessingStages';

function ClaimStatus() {
  const { claimId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/api/v1/claims/${claimId}/status`
        );
        
        if (!response.ok) {
          throw new Error('Claim not found');
        }
        
        const data = await response.json();
        setStatus(data);
        setError(null);
        
        // Stop polling when complete
        if (data.progress_percentage === 100) {
          setAutoRefresh(false);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();

    // Auto-refresh while processing
    const interval = autoRefresh ? setInterval(fetchStatus, 2000) : null;
    return () => interval && clearInterval(interval);
  }, [claimId, autoRefresh]);

  const handleViewDecision = () => {
    navigate(`/claim/${claimId}/decision`);
  };

  if (loading) {
    return (
      <div className="claim-status">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading claim status...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="claim-status">
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

  const statusColors = {
    'APPROVED': '#4CAF50',
    'REJECTED': '#f44336',
    'MANUAL_REVIEW': '#FF9800',
    'PROCESSING': '#2196F3'
  };

  return (
    <div className="claim-status">
      <div className="status-container">
        
        {/* Header */}
        <div className="status-header">
          <h1>📊 Claim Processing Status</h1>
          <div className="claim-id-box">
            <span className="label">Claim ID:</span>
            <span className="claim-id">{claimId}</span>
            <button
              className="copy-btn"
              onClick={() => navigator.clipboard.writeText(claimId)}
              title="Copy to clipboard"
            >
              📋
            </button>
          </div>
        </div>

        {/* Status Badge */}
        <div className="status-badge-container">
          <div
            className={`status-badge ${status.status.toLowerCase()}`}
            style={{ borderColor: statusColors[status.status] || '#2196F3' }}
          >
            <span className="status-label">{status.status}</span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="progress-section">
          <div className="progress-header">
            <span>Processing Progress</span>
            <span className="progress-percent">{status.progress_percentage}%</span>
          </div>
          <div className="progress-bar-container">
            <div
              className="progress-bar"
              style={{ width: `${status.progress_percentage}%` }}
            />
          </div>
        </div>

        {/* Processing Stages */}
        <ProcessingStages 
          currentStage={status.current_stage}
          progressPercentage={status.progress_percentage}
        />

        {/* Stage Details */}
        <div className="stage-details">
          <h3>Current Stage</h3>
          <div className="stage-info">
            <span className="stage-name">{status.current_stage}</span>
            {status.progress_percentage === 100 && (
              <span className="stage-complete">✓ Complete</span>
            )}
          </div>
        </div>

        {/* Decision Preview (if available) */}
        {status.latest_decision && (
          <div className="decision-preview">
            <h3>📋 Decision Summary</h3>
            <div className="decision-box">
              <div className="decision-item">
                <span className="label">Decision:</span>
                <span className={`value decision-${status.latest_decision.toLowerCase()}`}>
                  {status.latest_decision}
                </span>
              </div>
              {status.payout_amount !== null && (
                <div className="decision-item">
                  <span className="label">Approved Payout:</span>
                  <span className="value payout">
                    ₹{status.payout_amount.toLocaleString('en-IN')}
                  </span>
                </div>
              )}
              <div className="decision-item">
                <span className="label">Last Updated:</span>
                <span className="value">
                  {new Date(status.last_updated).toLocaleString()}
                </span>
              </div>
            </div>
            
            <button
              className="btn btn-primary full-width"
              onClick={handleViewDecision}
            >
              📄 View Full Decision & Explanation
            </button>
          </div>
        )}

        {/* Actions */}
        <div className="status-actions">
          <button
            className="btn btn-secondary"
            onClick={() => window.location.reload()}
          >
            🔄 Refresh Status
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => navigate('/')}
          >
            ➕ File Another Claim
          </button>
        </div>

        {/* Info Box */}
        <div className="info-box">
          <h4>💡 Need Help?</h4>
          <p>
            Your claim is being processed through our AI-powered FNOL system.
            You'll receive updates as it progresses through each stage.
            Processing typically completes in under 60 seconds.
          </p>
        </div>
      </div>
    </div>
  );
}

export default ClaimStatus;
