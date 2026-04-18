import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/ClaimSubmission.css';
import MediaUpload from '../components/MediaUpload';
import FormValidator from '../components/FormValidator';

function ClaimSubmission() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    policy_id: '',
    claim_type: 'motor',
    incident_description: '',
    incident_date: '',
    incident_location: '',
  });
  const [media, setMedia] = useState([]);
  const [errors, setErrors] = useState({});

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const handleMediaChange = (files) => {
    setMedia(files);
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) newErrors.name = 'Name is required';
    if (!formData.email.includes('@')) newErrors.email = 'Valid email is required';
    if (!/^\d{10,}$/.test(formData.phone.replace(/\D/g, ''))) {
      newErrors.phone = 'Phone must be at least 10 digits';
    }
    if (!formData.policy_id.trim()) newErrors.policy_id = 'Policy ID is required';
    if (!formData.incident_description.trim()) {
      newErrors.incident_description = 'Description is required';
    }
    if (formData.incident_description.length < 10) {
      newErrors.incident_description = 'Description must be at least 10 characters';
    }
    if (!formData.incident_date) newErrors.incident_date = 'Incident date is required';
    if (media.length === 0) newErrors.media = 'At least one image/video is required';

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const formPayload = new FormData();
      formPayload.append('name', formData.name);
      formPayload.append('email', formData.email);
      formPayload.append('phone', formData.phone);
      formPayload.append('policy_id', formData.policy_id);
      formPayload.append('claim_type', formData.claim_type);
      formPayload.append('incident_description', formData.incident_description);
      formPayload.append('incident_date', new Date(formData.incident_date).toISOString());
      formPayload.append('incident_location', formData.incident_location || '');

      // Add media files
      media.forEach((file) => {
        formPayload.append('media_files', file);
      });

      const response = await fetch('http://localhost:8000/api/v1/claims/submit', {
        method: 'POST',
        body: formPayload,
      });

      if (!response.ok) {
        throw new Error('Failed to submit claim');
      }

      const data = await response.json();
      
      // Redirect to status page
      navigate(`/claim/${data.claim_id}/status`, {
        state: { claimId: data.claim_id, message: data.message }
      });

    } catch (error) {
      console.error('Error:', error);
      setErrors({ submit: error.message || 'Failed to submit claim' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="claim-submission">
      <div className="submission-container">
        <div className="form-header">
          <h1>📋 File Your Insurance Claim</h1>
          <p>Complete in under 60 seconds with ClaimFast</p>
        </div>

        {errors.submit && (
          <div className="alert alert-error">
            {errors.submit}
          </div>
        )}

        <form onSubmit={handleSubmit} className="claim-form">
          
          {/* Personal Information Section */}
          <fieldset className="form-section">
            <legend>👤 Personal Information</legend>
            
            <div className="form-group">
              <label htmlFor="name">Full Name *</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                placeholder="Enter your full name"
                className={errors.name ? 'error' : ''}
              />
              {errors.name && <span className="error-message">{errors.name}</span>}
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="email">Email Address *</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  placeholder="you@example.com"
                  className={errors.email ? 'error' : ''}
                />
                {errors.email && <span className="error-message">{errors.email}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="phone">Phone Number *</label>
                <input
                  type="tel"
                  id="phone"
                  name="phone"
                  value={formData.phone}
                  onChange={handleInputChange}
                  placeholder="+91 XXXXX XXXXX"
                  className={errors.phone ? 'error' : ''}
                />
                {errors.phone && <span className="error-message">{errors.phone}</span>}
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="policy_id">Policy ID *</label>
              <input
                type="text"
                id="policy_id"
                name="policy_id"
                value={formData.policy_id}
                onChange={handleInputChange}
                placeholder="e.g., POL123456789"
                className={errors.policy_id ? 'error' : ''}
              />
              {errors.policy_id && <span className="error-message">{errors.policy_id}</span>}
            </div>
          </fieldset>

          {/* Claim Information Section */}
          <fieldset className="form-section">
            <legend>📝 Claim Information</legend>
            
            <div className="form-group">
              <label htmlFor="claim_type">Type of Insurance *</label>
              <select
                id="claim_type"
                name="claim_type"
                value={formData.claim_type}
                onChange={handleInputChange}
              >
                <option value="motor">🚗 Motor (Car/Bike/Vehicle)</option>
                <option value="health">🏥 Health (Medical)</option>
                <option value="property">🏠 Property (House/Building)</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="incident_date">Incident Date *</label>
              <input
                type="datetime-local"
                id="incident_date"
                name="incident_date"
                value={formData.incident_date}
                onChange={handleInputChange}
                className={errors.incident_date ? 'error' : ''}
              />
              {errors.incident_date && <span className="error-message">{errors.incident_date}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="incident_location">Incident Location</label>
              <input
                type="text"
                id="incident_location"
                name="incident_location"
                value={formData.incident_location}
                onChange={handleInputChange}
                placeholder="Enter incident location"
              />
            </div>

            <div className="form-group">
              <label htmlFor="incident_description">Incident Description *</label>
              <textarea
                id="incident_description"
                name="incident_description"
                value={formData.incident_description}
                onChange={handleInputChange}
                placeholder="Describe what happened (minimum 10 characters)"
                rows="5"
                className={errors.incident_description ? 'error' : ''}
              />
              <small>{formData.incident_description.length}/500 characters</small>
              {errors.incident_description && <span className="error-message">{errors.incident_description}</span>}
            </div>
          </fieldset>

          {/* Media Upload Section */}
          <fieldset className="form-section">
            <legend>📸 Upload Evidence</legend>
            <MediaUpload 
              onMediaChange={handleMediaChange}
              maxFiles={5}
              error={errors.media}
            />
            {errors.media && <span className="error-message">{errors.media}</span>}
          </fieldset>

          {/* Submit Button */}
          <div className="form-actions">
            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? '⏳ Submitting Claim...' : '✓ Submit Claim'}
            </button>
          </div>
        </form>

        <div className="info-box">
          <h3>⚡ Lightning Fast Processing</h3>
          <ul>
            <li>✓ AI-powered damage assessment</li>
            <li>✓ Instant policy verification</li>
            <li>✓ Fraud risk analysis</li>
            <li>✓ Decision in under 60 seconds</li>
            <li>✓ IRDAI compliant</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default ClaimSubmission;
