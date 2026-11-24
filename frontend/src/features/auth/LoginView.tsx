import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch } from '@/store/hooks';
import { setUser } from '@/store/slices/authSlice';
import { Lock, Mail } from 'lucide-react';

export const LoginView: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [email, setEmail] = useState('lead.investigator@pharmagmp.com');
  const [password, setPassword] = useState('demoPassword123!');

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    dispatch(
      setUser({
        token: 'jwt_mock_token_for_foundation',
        user: {
          id: 'usr_01h89qa1',
          email,
          fullName: 'Dr. Evelyn Vance, QA Lead',
          department: 'API Quality Assurance & Regulatory',
          role: 'QA_INVESTIGATOR',
          isActive: true,
        },
      })
    );
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-12 h-12 rounded-lg bg-sky-700 text-white font-bold text-xl flex items-center justify-center mx-auto shadow-md border border-sky-500/50">
          PR
        </div>
        <h2 className="mt-4 text-xl font-bold tracking-tight text-white font-sans">
          PharmaRCA Enterprise Platform
        </h2>
        <p className="mt-1 text-xs text-slate-400">
          FDA 21 CFR Part 11 Compliant Authentication Gateway
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-xl sm:rounded-lg sm:px-10 border border-slate-200">
          <form className="space-y-5" onSubmit={handleLogin}>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Corporate Email Address
              </label>
              <div className="mt-1.5 relative rounded-md shadow-xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-4 w-4 text-slate-400" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="block w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Authentication Password
              </label>
              <div className="mt-1.5 relative rounded-md shadow-xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-slate-400" />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="block w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 focus:outline-none"
            >
              Sign In to Quality System
            </button>
          </form>

          <div className="mt-6 border-t border-slate-200 pt-4 text-center">
            <span className="text-[10px] text-slate-400 font-mono">
              Authorized Quality Unit & API Manufacturing Personnel Only
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
