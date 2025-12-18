/**
 * EscalateSafe - Main App Component with Preview Integration
 */

import React, { useState, useEffect } from 'react';
import Preview from './components/Preview';
import './App.css';

declare const ZAFClient: any;

interface TicketData {
    id: string;
    subject: string;
    status: string;
    requester: { name: string; email: string };
}

type AppState = 'idle' | 'generating' | 'preview' | 'exporting' | 'exported' | 'failed' | 'cancelled';

interface PreviewData {
    redactedText: string;
    entityCounts: Record<string, number>;
    totalRedactions: number;
}

function App() {
    const [client, setClient] = useState<any>(null);
    const [ticket, setTicket] = useState<TicketData | null>(null);
    const [state, setState] = useState<AppState>('idle');
    const [apiBaseUrl, setApiBaseUrl] = useState<string>('http://localhost:8000');
    const [runId, setRunId] = useState<number | null>(null);
    const [previewData, setPreviewData] = useState<PreviewData | null>(null);
    const [error, setError] = useState<string>('');

    useEffect(() => {
        const zafClient = ZAFClient.init();
        setClient(zafClient);

        zafClient.get('ticket').then((data: any) => {
            setTicket({
                id: data.ticket.id,
                subject: data.ticket.subject,
                status: data.ticket.status,
                requester: {
                    name: data.ticket.requester?.name || 'Unknown',
                    email: data.ticket.requester?.email || 'unknown@example.com'
                }
            });
        });

        zafClient.get('setting:api_base_url').then((data: any) => {
            setApiBaseUrl(data['setting:api_base_url'] || 'http://localhost:8000');
        });

        zafClient.invoke('resize', { width: '100%', height: '600px' });
    }, []);

    const pollRunStatus = async (id: number) => {
        const maxAttempts = 30;
        let attempts = 0;

        const poll = async () => {
            try {
                const response = await fetch(`${apiBaseUrl}/v1/runs/${id}`);
                if (!response.ok) throw new Error('Failed to fetch run status');

                const data = await response.json();

                if (data.status === 'ready_for_review') {
                    const previewResponse = await fetch(`${apiBaseUrl}/v1/runs/${id}/preview/text`);
                    if (!previewResponse.ok) throw new Error('Failed to fetch preview');

                    const preview = await previewResponse.json();
                    setPreviewData({
                        redactedText: preview.redacted_text,
                        entityCounts: preview.redaction_summary.entities_redacted,
                        totalRedactions: preview.redaction_summary.total_redactions
                    });
                    setState('preview');
                    return;
                }

                if (data.status === 'failed') {
                    setError('Failed to process ticket');
                    setState('failed');
                    return;
                }

                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(poll, 2000);
                } else {
                    setError('Timeout waiting for preview');
                    setState('failed');
                }
            } catch (err: any) {
                setError(err.message || 'Unknown error');
                setState('failed');
            }
        };

        poll();
    };

    const handleGeneratePack = async () => {
        if (!ticket) return;

        setState(' generating');
        setError('');

        try {
            const response = await fetch(`${apiBaseUrl}/v1/runs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ticket_id: ticket.id,
                    include_internal_notes: false,
                    include_last_public_comments: 1
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to create run');
            }

            const data = await response.json();
            setRunId(data.run_id);
            pollRunStatus(data.run_id);

        } catch (err: any) {
            setError(err.message || 'Failed to generate pack');
            setState('failed');
        }
    };

    const handleApprove = async () => {
        setState('exporting');
        setTimeout(() => setState('exported'), 1000);
    };

    const handleCancel = async () => {
        if (runId) {
            await fetch(`${apiBaseUrl}/v1/runs/${runId}/cancel`, { method: 'POST' });
        }
        setState('cancelled');
    };

    if (!ticket) {
        return <div className="app-container"><div className="loading">Loading ticket data...</div></div>;
    }

    return (
        <div className="app-container">
            <div className="header">
                <h2>EscalateSafe</h2>
                <p className="subtitle">PII-Safe Escalation to Engineering</p>
            </div>

            <div className="ticket-context">
                <div className="ticket-field"><label>Ticket ID:</label><span>#{ticket.id}</span></div>
                <div className="ticket-field"><label>Subject:</label><span>{ticket.subject}</span></div>
                <div className="ticket-field"><label>Status:</label><span className="badge">{ticket.status}</span></div>
                <div className="ticket-field"><label>Requester:</label><span>{ticket.requester.name}</span></div>
            </div>

            <div className="actions">
                {state === 'idle' && (
                    <button className="btn-primary" onClick={handleGeneratePack}>Generate Engineering Pack</button>
                )}

                {state === 'generating' && (
                    <div className="status">
                        <div className="spinner"></div>
                        <p>Sanitizing ticket content...</p>
                        <small>Detecting and redacting PII</small>
                    </div>
                )}

                {state === 'preview' && previewData && (
                    <Preview
                        redactedText={previewData.redactedText}
                        entityCounts={previewData.entityCounts}
                        totalRedactions={previewData.totalRedactions}
                        onApprove={handleApprove}
                        onCancel={handleCancel}
                    />
                )}

                {state === 'exporting' && (
                    <div className="status"><div className="spinner"></div><p>Creating Jira issue...</p></div>
                )}

                {state === 'exported' && (
                    <div className="success">
                        <p>✅ Successfully exported!</p>
                        <p className="note">(Jira integration in M2)</p>
                        <button className="btn-secondary" onClick={() => setState('idle')}>Create Another</button>
                    </div>
                )}

                {state === 'failed' && (
                    <div className="error">
                        <p>❌ {error || 'Failed to generate pack'}</p>
                        <button className="btn-secondary" onClick={() => setState('idle')}>Try Again</button>
                    </div>
                )}

                {state === 'cancelled' && (
                    <div className="info">
                        <p>🚫 Run cancelled</p>
                        <button className="btn-secondary" onClick={() => setState('idle')}>Back</button>
                    </div>
                )}
            </div>

            <div className="footer"><small>v0.2.0 - M1 Text Redaction</small></div>
        </div>
    );
}

export default App;
