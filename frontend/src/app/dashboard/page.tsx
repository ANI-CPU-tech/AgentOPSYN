
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { fetchWithAuth } from '../../utils/api';
import IntegrationsManager from '../../components/IntegrationManager';
import AgentChat from '@/components/AgentChat';

interface UserProfile {
  id?: string;
  email?: string;
  org?: string;
  [key: string]: any; 
}

interface Team {
  id: string;
  name: string;
  repo_full_name: string;
  [key: string]: any;
}

export default function DashboardPage() {
  const router = useRouter();
  
  const [user, setUser] = useState<UserProfile | null>(null);
  const [teams, setTeams] = useState<Team[]>([]); 
  const [showProfile, setShowProfile] = useState<boolean>(false);
  
  const [teamName, setTeamName] = useState<string>('');
  const [repoName, setRepoName] = useState<string>('');
  const [joinTeamId, setJoinTeamId] = useState<string>('');

  useEffect(() => {
    loadUserProfile();
    loadTeams(); 
  }, []);

  const loadUserProfile = async () => {
    try {
      const res = await fetchWithAuth('/auth/me/');
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      }
    } catch (e) {
      console.error("Failed to load user", e);
    }
  };

  const loadTeams = async () => {
    try {
      const res = await fetchWithAuth('/auth/teams/'); 
      if (res.ok) {
        const data = await res.json();
        setTeams(data.results ? data.results : data);
      }
    } catch (e) {
      console.error("Failed to load teams", e);
    }
  };

  const handleJoinTeam = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!user || !user.id) {
      alert("User ID not found. Try logging in again.");
      return;
    }

    const res = await fetchWithAuth(`/auth/users/${user.id}/team/`, {
      method: 'POST', 
      body: JSON.stringify({ team_id: joinTeamId }),
    });

    if (res.ok) {
      setJoinTeamId('');
      loadUserProfile(); 
      loadTeams();       
    } else {
      const err = await res.json();
      alert('Error joining team: ' + JSON.stringify(err));
    }
  };

  const handleCreateTeam = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const res = await fetchWithAuth('/auth/teams/', {
      method: 'POST',
      body: JSON.stringify({ name: teamName, repo_full_name: repoName }),
    });

    if (res.ok) {
      setTeamName('');
      setRepoName('');
      loadUserProfile();
      loadTeams(); 
    } else {
      const err = await res.json();
      alert('Error creating team: ' + JSON.stringify(err));
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('token');
    router.push('/login');
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-[#161722] flex items-center justify-center">
        <div className="flex items-center gap-3 text-white font-mono">
          <div className="w-4 h-4 bg-rose-500 rounded-full animate-pulse"></div>
          Initializing Terminal...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#161722] flex font-sans overflow-hidden">
      
      {/* -------------------------------------------------------------------------
          LEFT SIDEBAR: NAVIGATION & TEAMS
      -------------------------------------------------------------------------- */}
      <div className="w-72 bg-[#1e2030] border-r border-gray-800 flex flex-col h-screen overflow-y-auto">
        
        {/* Logo Area */}
        <div className="p-6 border-b border-gray-800/50">
          <h1 className="text-2xl font-bold text-white tracking-widest uppercase flex items-center gap-2">
            OPSYN
            <span className="w-2 h-2 bg-rose-500 rounded-full"></span>
          </h1>
          <p className="text-[10px] text-gray-500 font-mono mt-1 tracking-widest uppercase">Agent Query Interface</p>
        </div>

        {/* Main Navigation (Knowledge Base) */}
        <div className="p-4">
          <h3 className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-3 px-2">Navigation</h3>
          <Link href="/runbooks" className="block w-full">
            <button className="w-full flex items-center gap-3 px-4 py-3 bg-gray-800/50 hover:bg-[#e03a55]/10 text-gray-300 hover:text-rose-400 rounded-lg transition-all text-sm font-medium border border-transparent hover:border-rose-500/30 group">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 group-hover:scale-110 transition-transform">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
              </svg>
              Runbook Registry
            </button>
          </Link>
        </div>

        {/* Teams Section */}
        <div className="px-4 py-2 flex-1">
          <h3 className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-3 px-2 mt-4">Workspaces</h3>
          
          {/* Active Teams List */}
          <div className="space-y-2 mb-6">
            {teams.length === 0 ? (
              <p className="text-xs text-gray-500 px-2 italic">No active workspaces.</p>
            ) : (
              teams.map((team) => (
                <div key={team.id} className="px-4 py-2 bg-gray-800/30 rounded-lg border border-gray-800 hover:border-gray-700 transition-colors">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                    <strong className="text-sm text-gray-200">{team.name}</strong>
                  </div>
                  <p className="text-[10px] text-gray-500 font-mono mt-1 truncate">{team.repo_full_name}</p>
                </div>
              ))
            )}
          </div>

          {/* Create Team Form */}
          <form onSubmit={handleCreateTeam} className="bg-[#161722] p-3 rounded-lg border border-gray-800/50 mb-4">
            <h4 className="text-xs font-semibold text-gray-400 mb-2">Create Workspace</h4>
            <input type="text" placeholder="Workspace Name" value={teamName} onChange={(e) => setTeamName(e.target.value)} required className="w-full bg-[#1e2030] text-white text-xs border border-gray-700 rounded px-2 py-1.5 mb-2 focus:border-rose-500 focus:outline-none placeholder-gray-600" />
            <input type="text" placeholder="GitHub Repo (owner/repo)" value={repoName} onChange={(e) => setRepoName(e.target.value)} required className="w-full bg-[#1e2030] text-white text-xs border border-gray-700 rounded px-2 py-1.5 mb-2 focus:border-rose-500 focus:outline-none placeholder-gray-600 font-mono" />
            <button type="submit" className="w-full bg-gray-800 hover:bg-gray-700 text-gray-300 text-[11px] font-bold py-1.5 rounded uppercase tracking-wider transition-colors">Create</button>
          </form>

          {/* Join Team Form */}
          <form onSubmit={handleJoinTeam} className="bg-[#161722] p-3 rounded-lg border border-gray-800/50 mb-4">
            <h4 className="text-xs font-semibold text-gray-400 mb-2">Join Workspace</h4>
            <input type="text" placeholder="Paste UUID..." value={joinTeamId} onChange={(e) => setJoinTeamId(e.target.value)} required className="w-full bg-[#1e2030] text-white text-xs border border-gray-700 rounded px-2 py-1.5 mb-2 focus:border-rose-500 focus:outline-none placeholder-gray-600 font-mono" />
            <button type="submit" className="w-full bg-gray-800 hover:bg-gray-700 text-gray-300 text-[11px] font-bold py-1.5 rounded uppercase tracking-wider transition-colors">Join</button>
          </form>
        </div>

        {/* Profile / Logout Section (Sticky Bottom) */}
        <div className="mt-auto border-t border-gray-800 p-4 bg-[#1e2030]">
          <button 
            onClick={() => setShowProfile(!showProfile)}
            className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-800 rounded-lg transition-colors group"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center border border-gray-600 text-white font-bold text-sm">
                {user.email?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="text-left">
                <p className="text-sm font-medium text-gray-200 truncate w-32">{user.email}</p>
                <p className="text-[10px] text-gray-500 font-mono">ID: {user.id?.substring(0,8)}...</p>
              </div>
            </div>
          </button>
          
          {showProfile && (
            <div className="mt-2 p-3 bg-[#161722] rounded-lg border border-gray-800">
              <button onClick={handleLogout} className="w-full text-left text-sm text-red-400 hover:text-red-300 flex items-center gap-2 py-1 transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
                </svg>
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>

      {/* -------------------------------------------------------------------------
          CENTER COLUMN: AGENT CHAT INTERFACE
      -------------------------------------------------------------------------- */}
      <div className="flex-1 flex flex-col h-screen bg-[#f8f9fa] relative">
        {/* Top Status Bar matching image */}
        <div className="absolute top-0 right-0 p-4 flex items-center gap-2 text-xs font-mono text-gray-500 bg-transparent z-10">
          LLM: llama3.2:3b <span className="w-1.5 h-1.5 bg-green-500 rounded-full ml-1"></span> READY
        </div>
        
        {/* Render the Agent Chat component full width of this center column */}
        <div className="flex-1 overflow-hidden">
          <AgentChat />
        </div>
      </div>

      {/* -------------------------------------------------------------------------
          RIGHT SIDEBAR: INTEGRATIONS
      -------------------------------------------------------------------------- */}
      <div className="w-80 bg-[#161722] border-l border-gray-800 h-screen overflow-y-auto p-4 hidden lg:block">
        <IntegrationsManager />
      </div>

    </div>
  );
}
