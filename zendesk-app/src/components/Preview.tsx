/**
 * Preview Component - Shows sanitized text and redaction report
 */

import React from 'react';
import './Preview.css';

interface RedactionReport {
    total_detections: number;
    entity_counts: Record<string, number>;
    low_confidence_count: number;
}

interface PreviewProps {
    redactedText: string;
    entityCounts: Record<string, number>;
    totalRedactions: number;
    onApprove: () => void;
    onCancel: () => void;
}

const Preview: React.FC<PreviewProps> = ({
    redactedText,
    entityCounts,
    totalRedactions,
    onApprove,
    onCancel
}) => {
    return (
        <div className="preview-container">
            <div className="preview-header">
                <h3>Sanitized Preview</h3>
                <span className="redaction-badge">
                    {totalRedactions} PII {totalRedactions === 1 ? 'entity' : 'entities'} redacted
                </span>
            </div>

            <div className="redaction-summary">
                <h4>Redaction Summary</h4>
                <div className="entity-counts">
                    {Object.entries(entityCounts).map(([entity, count]) => (
                        <div key={entity} className="entity-count-item">
                            <span className="entity-type">{entity.replace('_', ' ')}</span>
                            <span className="entity-value">{count}</span>
                        </div>
                    ))}
                </div>
            </div>

            <div className="preview-text-container">
                <h4>Sanitized Text</h4>
                <div className="preview-text">
                    {redactedText}
                </div>
            </div>

            <div className="preview-actions">
                <button className="btn-primary" onClick={onApprove}>
                    ✓ Approve & Create Jira Issue
                </button>
                <button className="btn-secondary" onClick={onCancel}>
                    Cancel
                </button>
            </div>

            <div className="preview-note">
                <small>
                    ⚠️ Review carefully before approving. Once exported to Jira, this action cannot be undone.
                </small>
            </div>
        </div>
    );
};

export default Preview;
