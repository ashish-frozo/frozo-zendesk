import React, { useState, useEffect } from 'react';
import './Settings.css';

interface SettingsProps {
    client: any;
    apiBaseUrl: string;
    tenantId: number;
}

type Tab = 'jira' | 'slack' | 'redaction';

const Settings: React.FC<SettingsProps> = ({ client, apiBaseUrl, tenantId }) => {
    const [activeTab, setActiveTab] = useState<Tab>('jira');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info', text: string } | null>(null);

    const showMessage = (type: 'success' | 'error' | 'info', text: string) => {
        setMessage({ type, text });
        setTimeout(() => setMessage(null), 5000);
    };

    return (
        <div className="settings-container">
            <div className="settings-header">
                <h2>⚙️ EscalateSafe Settings</h2>
                <p className="settings-description">
                    Configure your integrations and PII detection preferences
                </p>
            </div>

            {message && (
                <div className={`message message-${message.type}`}>
                    {message.type === 'success' && '✅ '}
                    {message.type === 'error' && '❌ '}
                    {message.type === 'info' && 'ℹ️ '}
                    {message.text}
                </div>
            )}

            <div className="settings-tabs">
                <button
                    className={`tab ${activeTab === 'jira' ? 'active' : ''}`}
                    onClick={() => setActiveTab('jira')}
                >
                    <span className="tab-icon">🎫</span>
                    Jira
                </button>
                <button
                    className={`tab ${activeTab === 'slack' ? 'active' : ''}`}
                    onClick={() => setActiveTab('slack')}
                >
                    <span className="tab-icon">💬</span>
                    Slack
                </button>
                <button
                    className={`tab ${activeTab === 'redaction' ? 'active' : ''}`}
                    onClick={() => setActiveTab('redaction')}
                >
                    <span className="tab-icon">🔒</span>
                    Redaction
                </button>
            </div>

            <div className="settings-content">
                {activeTab === 'jira' && (
                    <JiraSettings
                        apiBaseUrl={apiBaseUrl}
                        tenantId={tenantId}
                        onMessage={showMessage}
                    />
                )}
                {activeTab === 'slack' && (
                    <SlackSettings
                        apiBaseUrl={apiBaseUrl}
                        tenantId={tenantId}
                        onMessage={showMessage}
                    />
                )}
                {activeTab === 'redaction' && (
                    <RedactionSettings
                        apiBaseUrl={apiBaseUrl}
                        tenantId={tenantId}
                        onMessage={showMessage}
                    />
                )}
            </div>
        </div>
    );
};

// Jira Settings Component
const JiraSettings: React.FC<{
    apiBaseUrl: string;
    tenantId: number;
    onMessage: (type: 'success' | 'error' | 'info', text: string) => void;
}> = ({ apiBaseUrl, tenantId, onMessage }) => {
    const [config, setConfig] = useState({
        server_url: '',
        email: '',
        api_token: '',
        project_key: '',
        issue_type: 'Task',
        priority: 'High',
        labels: ['support-escalation', 'escalatesafe']
    });
    const [loading, setLoading] = useState(false);
    const [testing, setTesting] = useState(false);
    const [connectionStatus, setConnectionStatus] = useState<string | null>(null);

    useEffect(() => {
        loadConfig();
    }, []);

    const loadConfig = async () => {
        setLoading(true);
        try {
            const response = await fetch(`${apiBaseUrl}/v1/config/tenants/${tenantId}/jira`);
            if (response.ok) {
                const data = await response.json();
                setConfig({
                    ...config,
                    server_url: data.server_url || '',
                    email: data.email || '',
                    project_key: data.project_key || '',
                    issue_type: data.issue_type || 'Task',
                    priority: data.priority || 'High',
                    labels: data.labels || ['support-escalation', 'escalatesafe']
                });
                setConnectionStatus(data.connection_status);
            }
        } catch (error) {
            console.error('Failed to load Jira config:', error);
        } finally {
            setLoading(false);
        }
    };

    const saveConfig = async () => {
        if (!config.server_url || !config.email || !config.api_token || !config.project_key) {
            onMessage('error', 'Please fill in all required fields');
            return;
        }

        setLoading(true);
        try {
            const response = await fetch(`${apiBaseUrl}/v1/config/tenants/${tenantId}/jira`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            if (response.ok) {
                onMessage('success', 'Jira configuration saved successfully');
                loadConfig();
            } else {
                const error = await response.json();
                onMessage('error', error.detail || 'Failed to save configuration');
            }
        } catch (error) {
            onMessage('error', 'Failed to save configuration');
        } finally {
            setLoading(false);
        }
    };

    const testConnection = async () => {
        setTesting(true);
        try {
            const response = await fetch(`${apiBaseUrl}/v1/config/tenants/${tenantId}/test-connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ service: 'jira' })
            });

            const result = await response.json();
            if (result.success) {
                onMessage('success', result.message);
                setConnectionStatus('connected');
            } else {
                onMessage('error', result.message);
                setConnectionStatus('failed');
            }
        } catch (error) {
            onMessage('error', 'Connection test failed');
            setConnectionStatus('failed');
        } finally {
            setTesting(false);
        }
    };

    return (
        <div className="settings-form">
            <div className="form-section">
                <h3>Jira Server</h3>
                <div className="form-group">
                    <label>Server URL *</label>
                    <input
                        type="url"
                        placeholder="https://your-company.atlassian.net"
                        value={config.server_url}
                        onChange={(e) => setConfig({ ...config, server_url: e.target.value })}
                    />
                    <span className="help-text">Your Jira Cloud URL</span>
                </div>

                <div className="form-group">
                    <label>Email *</label>
                    <input
                        type="email"
                        placeholder="your-email@company.com"
                        value={config.email}
                        onChange={(e) => setConfig({ ...config, email: e.target.value })}
                    />
                    <span className="help-text">Jira account email</span>
                </div>

                <div className="form-group">
                    <label>API Token *</label>
                    <input
                        type="password"
                        placeholder="Enter your Jira API token"
                        value={config.api_token}
                        onChange={(e) => setConfig({ ...config, api_token: e.target.value })}
                    />
                    <span className="help-text">
                        <a href="https://id.atlassian.com/manage-profile/security/api-tokens" target="_blank">
                            Generate API token
                        </a>
                    </span>
                </div>
            </div>

            <div className="form-section">
                <h3>Default Issue Settings</h3>
                <div className="form-row">
                    <div className="form-group">
                        <label>Project Key *</label>
                        <input
                            type="text"
                            placeholder="SCRUM"
                            value={config.project_key}
                            onChange={(e) => setConfig({ ...config, project_key: e.target.value.toUpperCase() })}
                        />
                    </div>

                    <div className="form-group">
                        <label>Issue Type</label>
                        <select
                            value={config.issue_type}
                            onChange={(e) => setConfig({ ...config, issue_type: e.target.value })}
                        >
                            <option value="Task">Task</option>
                            <option value="Bug">Bug</option>
                            <option value="Story">Story</option>
                        </select>
                    </div>

                    <div className="form-group">
                        <label>Priority</label>
                        <select
                            value={config.priority}
                            onChange={(e) => setConfig({ ...config, priority: e.target.value })}
                        >
                            <option value="Highest">Highest</option>
                            <option value="High">High</option>
                            <option value="Medium">Medium</option>
                            <option value="Low">Low</option>
                        </select>
                    </div>
                </div>
            </div>

            <div className="form-actions">
                <button
                    className="btn-secondary"
                    onClick={testConnection}
                    disabled={testing || !config.server_url}
                >
                    {testing ? '🔄 Testing...' : '🔌 Test Connection'}
                </button>
                <button
                    className="btn-primary"
                    onClick={saveConfig}
                    disabled={loading}
                >
                    {loading ? '💾 Saving...' : '💾 Save Configuration'}
                </button>
            </div>

            {connectionStatus && (
                <div className={`connection-status status-${connectionStatus}`}>
                    {connectionStatus === 'connected' && '✅ Connected'}
                    {connectionStatus === 'failed' && '❌ Connection Failed'}
                </div>
            )}
        </div>
    );
};

// Slack Settings Component
const SlackSettings: React.FC<{
    apiBaseUrl: string;
    tenantId: number;
    onMessage: (type: 'success' | 'error' | 'info', text: string) => void;
}> = ({ apiBaseUrl, tenantId, onMessage }) => {
    const [config, setConfig] = useState({
        webhook_url: '',
        channel: '',
        enabled: true
    });
    const [loading, setLoading] = useState(false);
    const [testing, setTesting] = useState(false);
    const [connectionStatus, setConnectionStatus] = useState<string | null>(null);

    useEffect(() => {
        loadConfig();
    }, []);

    const loadConfig = async () => {
        setLoading(true);
        try {
            const response = await fetch(`${apiBaseUrl}/v1/config/tenants/${tenantId}/slack`);
            if (response.ok) {
                const data = await response.json();
                setConfig({
                    webhook_url: '', // Never load the actual webhook
                    channel: data.channel || '',
                    enabled: data.enabled
                });
                setConnectionStatus(data.connection_status);
            }
        } catch (error) {
            console.error('Failed to load Slack config:', error);
        } finally {
            setLoading(false);
        }
    };

    const saveConfig = async () => {
        if (!config.webhook_url) {
            onMessage('error', 'Please enter a Slack webhook URL');
            return;
        }

        setLoading(true);
        try {
            const response = await fetch(`${apiBaseUrl}/v1/config/tenants/${tenantId}/slack`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            if (response.ok) {
                onMessage('success', 'Slack configuration saved successfully');
                loadConfig();
            } else {
                const error = await response.json();
                onMessage('error', error.detail || 'Failed to save configuration');
            }
        } catch (error) {
            onMessage('error', 'Failed to save configuration');
        } finally {
            setLoading(false);
        }
    };

    const testConnection = async () => {
        setTesting(true);
        try {
            const response = await fetch(`${apiBaseUrl}/v1/config/tenants/${tenantId}/test-connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ service: 'slack' })
            });

            const result = await response.json();
            if (result.success) {
                onMessage('success', result.message);
                setConnectionStatus('connected');
            } else {
                onMessage('error', result.message);
                setConnectionStatus('failed');
            }
        } catch (error) {
            onMessage('error', 'Connection test failed');
            setConnectionStatus('failed');
        } finally {
            setTesting(false);
        }
    };

    return (
        <div className="settings-form">
            <div className="form-section">
                <h3>Slack Webhook</h3>
                <div className="form-group">
                    <label>Webhook URL *</label>
                    <input
                        type="url"
                        placeholder="https://hooks.slack.com/services/..."
                        value={config.webhook_url}
                        onChange={(e) => setConfig({ ...config, webhook_url: e.target.value })}
                    />
                    <span className="help-text">
                        <a href="https://api.slack.com/messaging/webhooks" target="_blank">
                            Create Slack webhook
                        </a>
                    </span>
                </div>

                <div className="form-group">
                    <label>Channel (optional)</label>
                    <input
                        type="text"
                        placeholder="#engineering"
                        value={config.channel}
                        onChange={(e) => setConfig({ ...config, channel: e.target.value })}
                    />
                    <span className="help-text">For display purposes only</span>
                </div>

                <div className="form-group checkbox-group">
                    <label>
                        <input
                            type="checkbox"
                            checked={config.enabled}
                            onChange={(e) => setConfig({ ...config, enabled: e.target.checked })}
                        />
                        <span>Enable Slack notifications</span>
                    </label>
                </div>
            </div>

            <div className="form-actions">
                <button
                    className="btn-secondary"
                    onClick={testConnection}
                    disabled={testing || !config.webhook_url}
                >
                    {testing ? '🔄 Testing...' : '🔌 Test Connection'}
                </button>
                <button
                    className="btn-primary"
                    onClick={saveConfig}
                    disabled={loading}
                >
                    {loading ? '💾 Saving...' : '💾 Save Configuration'}
                </button>
            </div>

            {connectionStatus && (
                <div className={`connection-status status-${connectionStatus}`}>
                    {connectionStatus === 'connected' && '✅ Connected'}
                    {connectionStatus === 'failed' && '❌ Connection Failed'}
                </div>
            )}
        </div>
    );
};

// Redaction Settings Component
const RedactionSettings: React.FC<{
    apiBaseUrl: string;
    tenantId: number;
    onMessage: (type: 'success' | 'error' | 'info', text: string) => void;
}> = ({ apiBaseUrl, tenantId, onMessage }) => {
    const [config, setConfig] = useState({
        confidence_threshold: 0.5,
        enable_indian_entities: false,
        enabled_entity_types: [
            'EMAIL_ADDRESS',
            'PHONE_NUMBER',
            'CREDIT_CARD',
            'PERSON',
            'LOCATION',
            'API_KEY'
        ],
        allow_internal_notes: false
    });
    const [loading, setLoading] = useState(false);

    const allEntityTypes = [
        'EMAIL_ADDRESS',
        'PHONE_NUMBER',
        'CREDIT_CARD',
        'PERSON',
        'LOCATION',
        'API_KEY',
        'US_SSN',
        'US_PASSPORT',
        'IBAN_CODE',
        'IP_ADDRESS',
        'DATE_TIME'
    ];

    useEffect(() => {
        loadConfig();
    }, []);

    const loadConfig = async () => {
        setLoading(true);
        try {
            const response = await fetch(`${apiBaseUrl}/v1/config/tenants/${tenantId}/redaction`);
            if (response.ok) {
                const data = await response.json();
                setConfig(data);
            }
        } catch (error) {
            console.error('Failed to load redaction config:', error);
        } finally {
            setLoading(false);
        }
    };

    const saveConfig = async () => {
        setLoading(true);
        try {
            const response = await fetch(`${apiBaseUrl}/v1/config/tenants/${tenantId}/redaction`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            if (response.ok) {
                onMessage('success', 'Redaction settings saved successfully');
            } else {
                const error = await response.json();
                onMessage('error', error.detail || 'Failed to save settings');
            }
        } catch (error) {
            onMessage('error', 'Failed to save settings');
        } finally {
            setLoading(false);
        }
    };

    const toggleEntityType = (entityType: string) => {
        if (config.enabled_entity_types.includes(entityType)) {
            setConfig({
                ...config,
                enabled_entity_types: config.enabled_entity_types.filter(t => t !== entityType)
            });
        } else {
            setConfig({
                ...config,
                enabled_entity_types: [...config.enabled_entity_types, entityType]
            });
        }
    };

    return (
        <div className="settings-form">
            <div className="form-section">
                <h3>Detection Settings</h3>
                <div className="form-group">
                    <label>
                        Confidence Threshold: {(config.confidence_threshold * 100).toFixed(0)}%
                    </label>
                    <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={config.confidence_threshold}
                        onChange={(e) => setConfig({ ...config, confidence_threshold: parseFloat(e.target.value) })}
                    />
                    <span className="help-text">
                        Lower = More detections (may have false positives), Higher = Fewer detections (more accurate)
                    </span>
                </div>

                <div className="form-group checkbox-group">
                    <label>
                        <input
                            type="checkbox"
                            checked={config.enable_indian_entities}
                            onChange={(e) => setConfig({ ...config, enable_indian_entities: e.target.checked })}
                        />
                        <span>Enable India-specific entities (Aadhaar, PAN, etc.)</span>
                    </label>
                </div>
            </div>

            <div className="form-section">
                <h3>Entity Types to Detect</h3>
                <div className="entity-types-grid">
                    {allEntityTypes.map(entityType => (
                        <label key={entityType} className="entity-type-checkbox">
                            <input
                                type="checkbox"
                                checked={config.enabled_entity_types.includes(entityType)}
                                onChange={() => toggleEntityType(entityType)}
                            />
                            <span>{entityType.replace(/_/g, ' ')}</span>
                        </label>
                    ))}
                </div>
            </div>

            <div className="form-section">
                <h3>Advanced Options</h3>
                <div className="form-group checkbox-group">
                    <label>
                        <input
                            type="checkbox"
                            checked={config.allow_internal_notes}
                            onChange={(e) => setConfig({ ...config, allow_internal_notes: e.target.checked })}
                        />
                        <span>Allow including internal notes in escalations</span>
                    </label>
                    <span className="help-text warning">
                        ⚠️ Internal notes may contain sensitive information
                    </span>
                </div>
            </div>

            <div className="form-actions">
                <button
                    className="btn-primary"
                    onClick={saveConfig}
                    disabled={loading}
                >
                    {loading ? '💾 Saving...' : '💾 Save Settings'}
                </button>
            </div>
        </div>
    );
};

export default Settings;
