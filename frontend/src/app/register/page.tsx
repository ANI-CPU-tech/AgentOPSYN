
// app/register/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  
  // Toggle state for Create vs Join
  const [isJoining, setIsJoining] = useState<boolean>(false);
  const [orgName, setOrgName] = useState<string>(''); 
  const [orgId, setOrgId] = useState<string>(''); 
  
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    // Build the payload dynamically based on what they are trying to do
    const payload: any = { email, password };
    if (isJoining) {
      payload.org_id = orgId;
    } else {
      payload.org_name = orgName;
    }

    try {
      const res = await fetch('http://localhost:8000/api/auth/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        alert('Registration successful! Please login.');
        router.push('/login');
      } else {
        const data = await res.json();
        setError(JSON.stringify(data));
      }
    } catch (err) {
      setError('Network error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#161722] flex items-center justify-center p-4 font-sans">
      <div className="w-full max-w-md bg-[#1e2030] rounded-xl shadow-2xl border border-gray-700/50 p-8">
        
        <div className="mb-6 text-center">
          <div className="text-xs font-mono text-rose-500 mb-2 uppercase tracking-widest">// System Access</div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Register for OPSYN</h1>
        </div>
        
        {/* 🚀 SEGMENTED TOGGLE BUTTONS */}
        <div className="flex p-1 bg-[#161722] rounded-lg mb-6 border border-gray-700/50">
          <button 
            type="button"
            onClick={() => setIsJoining(false)} 
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${!isJoining ? 'bg-[#1e2030] text-white shadow' : 'text-gray-400 hover:text-white'}`}
          >
            Create Workspace
          </button>
          <button 
            type="button"
            onClick={() => setIsJoining(true)}
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${isJoining ? 'bg-[#1e2030] text-white shadow' : 'text-gray-400 hover:text-white'}`}
          >
            Join Workspace
          </button>
        </div>

        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Email</label>
            <input 
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              required 
              className="w-full bg-[#161722] text-white border border-gray-600 rounded-lg py-2.5 px-4 focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 transition-all placeholder-gray-500"
              placeholder="engineer@company.com"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
              className="w-full bg-[#161722] text-white border border-gray-600 rounded-lg py-2.5 px-4 focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 transition-all placeholder-gray-500"
              placeholder="••••••••"
            />
          </div>

          {/* 🚀 DYNAMIC INPUT FIELDS */}
          <div className="pt-2 border-t border-gray-700/50 mt-4">
            {isJoining ? (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Invite Code (Org ID)</label>
                <input 
                  type="text" 
                  placeholder="e.g., 550e8400-e29b-41d4-a716-446655440000"
                  value={orgId} 
                  onChange={(e) => setOrgId(e.target.value)} 
                  required 
                  className="w-full bg-[#161722] text-white border border-gray-600 rounded-lg py-2.5 px-4 focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 transition-all font-mono text-sm placeholder-gray-600"
                />
              </div>
            ) : (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Organization Name</label>
                <input 
                  type="text" 
                  value={orgName} 
                  onChange={(e) => setOrgName(e.target.value)} 
                  required 
                  className="w-full bg-[#161722] text-white border border-gray-600 rounded-lg py-2.5 px-4 focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 transition-all placeholder-gray-500"
                  placeholder="Acme Corp Engineering"
                />
              </div>
            )}
          </div>

          {error && (
            <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-3 mt-4">
              <p className="text-red-400 text-sm font-mono break-words">{error}</p>
            </div>
          )}

          <button 
            type="submit" 
            disabled={isLoading}
            className="w-full bg-[#e03a55] hover:bg-[#c22e45] text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2 mt-6 disabled:opacity-50"
          >
            {isLoading ? 'Registering...' : 'REGISTER →'}
          </button>
        </form>
        
        <p className="text-center text-gray-400 text-sm mt-6">
          Already have an account? <Link href="/login" className="text-white hover:text-rose-400 font-medium transition-colors">Login here</Link>
        </p>
      </div>
    </div>
  );
}
