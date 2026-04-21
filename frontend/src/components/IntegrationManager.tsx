
'use client';

import { useEffect, useState } from 'react';
import { fetchWithAuth } from '../utils/api';

interface Integration {
  id: string;
  source: string;
  is_active: boolean;
  last_synced_at: string | null;
  created_at: string;
}

export default function IntegrationsManager() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [source, setSource] = useState<string>('github');
  const [isLoading, setIsLoading] = useState(false);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  
  // Generic state for dynamic config inputs
  const [config, setConfig] = useState<Record<string, string>>({});

  useEffect(() => {
    loadIntegrations();
  }, []);

  const loadIntegrations = async () => {
    try {
      const res = await fetchWithAuth('/integrations/');
      if (res.ok) {
        const data = await res.json();
        setIntegrations(data.results ? data.results : data);
      }
    } catch (err) {
      console.error("Failed to load integrations", err);
    }
  };

  const handleInputChange = (key: string, value: string) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleConnect = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);

    // Format specific payload requirements before sending
    let finalConfig: any = { ...config };
    if (source === 'github' && config.repositories) {
      // GitHub expects an array of repos, so we split the comma-separated string
      finalConfig.repositories = config.repositories.split(',').map(r => r.trim());
    }

    try {
      const res = await fetchWithAuth('/integrations/', {
        method: 'POST',
        body: JSON.stringify({
          source: source,
          config: finalConfig
        }),
      });

      if (res.ok) {
        setConfig({}); // clear form
        loadIntegrations();
      } else {
        const err = await res.json();
        alert('Error connecting integration: ' + JSON.stringify(err));
      }
    } catch (err) {
      alert('Network error connecting integration.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleManualSync = async (id: string) => {
    setSyncingId(id);
    try {
      // Triggers the Celery task in the backend via a PATCH request
      const res = await fetchWithAuth(`/integrations/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: true }),
      });

      if (res.ok) {
        // Wait a second before reloading to give Celery a head start
        setTimeout(loadIntegrations, 1000); 
      } else {
        alert('Failed to trigger sync.');
      }
    } catch (err) {
      alert('Network error while syncing.');
    } finally {
      setSyncingId(null);
    }
  };

  // Helper to format source names
  const formatSource = (src: string) => src.charAt(0).toUpperCase() + src.slice(1);

  return (
    <div className="bg-[#1e2030] rounded-xl shadow-2xl border border-gray-700/50 p-6 flex flex-col h-full font-sans text-gray-200">
      
      {/* Header */}
      <div className="flex items-center gap-3 mb-6 pb-4 border-b border-gray-700/50">
        <div className="w-8 h-8 rounded bg-rose-500/20 text-rose-400 flex items-center justify-center">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-white tracking-tight">Integrations Hub</h2>
      </div>
      
      {/* List Existing Integrations */}
      <div className="mb-8">
        <h3 className="text-xs font-mono text-gray-500 uppercase tracking-widest mb-3">Active Connections</h3>
        
        {integrations.length === 0 ? (
          <div className="text-center py-6 bg-[#161722] rounded-lg border border-dashed border-gray-700 text-gray-500 text-sm">
            No data sources connected yet.
          </div>
        ) : (
          <div className="space-y-3">
            {integrations.map((intg) => (
              <div key={intg.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-[#161722] rounded-lg border border-gray-700/50 hover:border-gray-600 transition-colors gap-4">
                
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-bold text-white">{formatSource(intg.source)}</span>
                    <span className={`flex items-center gap-1 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full ${intg.is_active ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${intg.is_active ? 'bg-green-400' : 'bg-red-400'}`}></span>
                      {intg.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 font-mono">
                    Synced: {intg.last_synced_at ? new Date(intg.last_synced_at).toLocaleString() : 'Never'}
                  </div>
                </div>

                <button 
                  onClick={() => handleManualSync(intg.id)} 
                  disabled={syncingId === intg.id}
                  className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold rounded border border-gray-600 transition-all disabled:opacity-50 whitespace-nowrap"
                >
                  {syncingId === intg.id ? 'Syncing...' : 'Force Sync'}
                </button>
                
              </div>
            ))}
          </div>
        )}
      </div>

      <hr className="border-gray-700/50 mb-6" />

      {/* Connect New Integration Form */}
      <div>
        <h3 className="text-xs font-mono text-rose-500 uppercase tracking-widest mb-4">// Add New Data Source</h3>
        
        <form onSubmit={handleConnect} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Platform</label>
            <select 
              value={source} 
              onChange={(e) => {
                setSource(e.target.value);
                setConfig({}); // reset fields when switching sources
              }}
              className="w-full bg-[#161722] text-white border border-gray-600 rounded-lg py-2.5 px-4 focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 transition-all appearance-none cursor-pointer"
            >
              <option value="github">GitHub</option>
              <option value="notion">Notion</option>
              <option value="jira">Jira</option>
              <option value="slack">Slack</option>
              <option value="datadog">Datadog</option>
            </select>
          </div>

          {/* Dynamic Inputs based on Source */}
          <div className="p-4 bg-[#161722] rounded-lg border border-gray-700/50 space-y-4">
            
            {source === 'github' && (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Personal Access Token</label>
                  <input type="password" required onChange={(e) => handleInputChange('token', e.target.value)} className="w-full bg-[#1e2030] text-white border border-gray-600 rounded py-2 px-3 focus:border-rose-500 focus:outline-none text-sm placeholder-gray-600" placeholder="ghp_xxxxxxxxxxxx" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Repositories (comma separated)</label>
                  <input type="text" required onChange={(e) => handleInputChange('repositories', e.target.value)} className="w-full bg-[#1e2030] text-white border border-gray-600 rounded py-2 px-3 focus:border-rose-500 focus:outline-none text-sm placeholder-gray-600 font-mono" placeholder="owner/repo1, owner/repo2" />
                </div>
              </>
            )}

            {source === 'notion' && (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Internal Integration Token</label>
                  <input type="password" required onChange={(e) => handleInputChange('token', e.target.value)} className="w-full bg-[#1e2030] text-white border border-gray-600 rounded py-2 px-3 focus:border-rose-500 focus:outline-none text-sm placeholder-gray-600" placeholder="secret_xxxxxxxxxxxx" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Workspace Name</label>
                  <input type="text" required onChange={(e) => handleInputChange('workspace', e.target.value)} className="w-full bg-[#1e2030] text-white border border-gray-600 rounded py-2 px-3 focus:border-rose-500 focus:outline-none text-sm placeholder-gray-600" placeholder="Engineering Wiki" />
                </div>
              </>
            )}

            {source === 'jira' && (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Domain URL</label>
                  <input type="url" required onChange={(e) => handleInputChange('domain', e.target.value)} className="w-full bg-[#1e2030] text-white border border-gray-600 rounded py-2 px-3 focus:border-rose-500 focus:outline-none text-sm placeholder-gray-600" placeholder="https://company.atlassian.net" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Account Email</label>
                  <input type="email" required onChange={(e) => handleInputChange('email', e.target.value)} className="w-full bg-[#1e2030] text-white border border-gray-600 rounded py-2 px-3 focus:border-rose-500 focus:outline-none text-sm placeholder-gray-600" placeholder="admin@company.com" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">API Token</label>
                  <input type="password" required onChange={(e) => handleInputChange('token', e.target.value)} className="w-full bg-[#1e2030] text-white border border-gray-600 rounded py-2 px-3 focus:border-rose-500 focus:outline-none text-sm placeholder-gray-600" placeholder="ATATT3xFfGF..." />
                </div>
              </>
            )}

            {source === 'slack' && (
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Webhook URL</label>
                <input type="url" required onChange={(e) => handleInputChange('webhook_url', e.target.value)} className="w-full bg-[#1e2030] text-white border border-gray-600 rounded py-2 px-3 focus:border-rose-500 focus:outline-none text-sm placeholder-gray-600" placeholder="https://hooks.slack.com/services/..." />
              </div>
            )}

            {source === 'datadog' && (
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">API Key</label>
                <input type="password" required onChange={(e) => handleInputChange('api_key', e.target.value)} className="w-full bg-[#1e2030] text-white border border-gray-600 rounded py-2 px-3 focus:border-rose-500 focus:outline-none text-sm placeholder-gray-600" placeholder="dd_api_xxxxxxxxxxxx" />
              </div>
            )}
          </div>

          <button 
            type="submit" 
            disabled={isLoading}
            className="w-full mt-2 bg-[#e03a55] hover:bg-[#c22e45] text-white font-bold py-3 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isLoading ? 'Connecting...' : `Connect ${formatSource(source)}`}
          </button>
        </form>
      </div>

    </div>
  );
}
