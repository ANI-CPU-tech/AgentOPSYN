
// app/login/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/auth/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (res.ok) {
        localStorage.setItem('access_token', data.access || data.token); 
        router.push('/dashboard');
      } else {
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
        
        <div className="mb-8 text-center">
          <div className="text-xs font-mono text-rose-500 mb-2 uppercase tracking-widest">// Authenticate</div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Login to OPSYN</h1>
          <p className="text-gray-400 mt-2 text-sm">Access your agent query interface and runbooks.</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-5">
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

          {error && (
            <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-3">
              <p className="text-red-400 text-sm font-mono break-words">{error}</p>
            </div>
          )}

          <button 
            type="submit" 
            disabled={isLoading}
            className="w-full bg-[#e03a55] hover:bg-[#c22e45] text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isLoading ? 'Authenticating...' : 'LOGIN →'}
          </button>
        </form>

        <p className="text-center text-gray-400 text-sm mt-6">
          No account? <Link href="/register" className="text-white hover:text-rose-400 font-medium transition-colors">Register here</Link>
        </p>
      </div>
    </div>
  );
}
