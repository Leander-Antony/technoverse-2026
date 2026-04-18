import React, { useState } from 'react';
import '../styles/MediaUpload.css';

function MediaUpload({ onMediaChange, maxFiles = 5, error }) {
  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);

  const handleFiles = (newFiles) => {
    const validFiles = Array.from(newFiles).filter(file => {
      const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'video/quicktime'];
      const validSize = file.size <= 50 * 1024 * 1024; // 50MB max
      return validTypes.includes(file.type) && validSize;
    });

    const combinedFiles = [...files, ...validFiles].slice(0, maxFiles);
    setFiles(combinedFiles);
    onMediaChange(combinedFiles);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleFileInput = (e) => {
    handleFiles(e.target.files);
  };

  const removeFile = (index) => {
    const newFiles = files.filter((_, i) => i !== index);
    setFiles(newFiles);
    onMediaChange(newFiles);
  };

  return (
    <div className="media-upload">
      <div
        className={`upload-area ${dragActive ? 'drag-active' : ''} ${error ? 'error' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <div className="upload-content">
          <svg className="upload-icon" viewBox="0 0 24 24">
            <path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
          </svg>
          <p>Drag and drop images/videos here</p>
          <p className="upload-text">or</p>
          <label className="upload-button">
            📁 Select Files
            <input
              type="file"
              multiple
              accept="image/*,video/*"
              onChange={handleFileInput}
              style={{ display: 'none' }}
            />
          </label>
          <p className="upload-hint">
            Supports: JPG, PNG, GIF, MP4, MOV (Max 50MB per file, up to {maxFiles} files)
          </p>
        </div>
      </div>

      {files.length > 0 && (
        <div className="file-list">
          <h4>Uploaded Files ({files.length}/{maxFiles}):</h4>
          <ul>
            {files.map((file, index) => (
              <li key={index} className="file-item">
                <span className="file-name">
                  {file.type.startsWith('image/') ? '📷' : '🎥'} {file.name}
                </span>
                <span className="file-size">
                  ({(file.size / 1024 / 1024).toFixed(2)} MB)
                </span>
                <button
                  type="button"
                  className="remove-btn"
                  onClick={() => removeFile(index)}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default MediaUpload;
