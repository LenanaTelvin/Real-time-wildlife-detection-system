// src/components/AIResults.jsx
import React from 'react';

/**
 * AIResults Component
 * 
 * Displays recent detection results from the AI model.
 * Shows species, confidence score, and timestamp for each detection.
 * 
 * Props:
 *   recentDetections {Array} - List of detection objects from the API
 *   onViewAll {Function} - Optional callback to view full history
 */

const AIResults = ({ recentDetections = [], onViewAll }) => {
  // Helper function to get species-specific CSS class
  const getSpeciesClass = (species) => {
    const classes = {
      lions: 'lion',
      hyenas: 'hyena',
      buffalo: 'buffalo',
    };
    return classes[species?.toLowerCase()] || '';
  };

  // Helper function to get species color
  const getSpeciesColor = (species) => {
    const colors = {
      lions: '#22c55e',
      hyenas: '#a855f7',
      buffalo: '#ef4444',
    };
    return colors[species?.toLowerCase()] || '#64748b';
  };

  // Format date for display
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  };

  // Get confidence color based on percentage
  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return '#22c55e';  // Green - High confidence
    if (confidence >= 0.6) return '#f59e0b';  // Yellow - Medium confidence
    return '#ef4444';                          // Red - Low confidence
  };

  return (
    <div className="ai-results-card">
      {/* Header */}
      <div className="panel-header">
        <span className="panel-title">
          <span>🤖</span> AI Results
        </span>
        <div className="header-actions">
          <span className="result-count">{recentDetections.length} recent</span>
          {onViewAll && (
            <button onClick={onViewAll} className="view-all-btn">
              View All →
            </button>
          )}
        </div>
      </div>

      {/* Results List */}
      <div className="results-list">
        {recentDetections.length === 0 ? (
          <div className="empty-results">
            <div className="empty-icon">🔍</div>
            <p>No detections yet</p>
            <p className="empty-hint">Upload a video to start detecting wildlife</p>
          </div>
        ) : (
          recentDetections.map((detection, index) => (
            <div 
              key={detection.id || index} 
              className={`result-item ${getSpeciesClass(detection.species)}`}
              style={{
                borderLeftColor: getSpeciesColor(detection.species),
              }}
            >
              <div className="result-header">
                <div className="result-species-info">
                  <span 
                    className="species-dot"
                    style={{ background: getSpeciesColor(detection.species) }}
                  />
                  <span className={`result-species ${getSpeciesClass(detection.species)}`}>
                    {detection.species}
                  </span>
                  {detection.confidence >= 0.85 && (
                    <span className="high-confidence-badge">High</span>
                  )}
                </div>
                <div className="result-confidence">
                  <div 
                    className="confidence-bar"
                    style={{ 
                      width: `${(detection.confidence || 0) * 100}%`,
                      background: getConfidenceColor(detection.confidence || 0)
                    }}
                  />
                  <span className="confidence-text">
                    {((detection.confidence || 0) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="result-footer">
                <span className="result-time">
                  🕐 {formatDate(detection.created_at) || `${detection.date} ${detection.timestamp}`}
                </span>
                {detection.source === 'video' && (
                  <span className="result-source">📹 Video</span>
                )}
                {detection.source === 'camera' && (
                  <span className="result-source">📷 Live</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer with tip */}
      {recentDetections.length > 0 && (
        <div className="results-footer">
          <p className="results-tip">
            💡 Tip: Higher confidence (80%+) means the AI is very sure
          </p>
        </div>
      )}
    </div>
  );
};

export default AIResults;