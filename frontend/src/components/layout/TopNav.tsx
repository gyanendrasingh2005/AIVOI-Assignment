import React, { useState, useEffect } from 'react';
import { 
  Menu, 
  Bell, 
  Shield, 
  Database, 
  Activity, 
  Search,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { toggleSidebar } from '@/store/slices/uiSlice';
import { systemService } from '@/services/systemService';

export const TopNav: React.FC = () => {
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const [dbStatus, setDbStatus] = useState<'checking' | 'connected' | 'offline'>('checking');
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  useEffect(() => {
    let isMounted = true;
    const checkSystemHealth = async () => {
      try {
        await systemService.getHealth();
        if (isMounted) setBackendStatus('online');
      } catch {
        if (isMounted) setBackendStatus('offline');
      }

      try {
        await systemService.getDbHealth();
        if (isMounted) setDbStatus('connected');
      } catch {
        if (isMounted) setDbStatus('offline');
      }
    };

    checkSystemHealth();
    const interval = setInterval(checkSystemHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shadow-xs sticky top-0 z-20">
      {/* Left: Sidebar Toggle & Search */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => dispatch(toggleSidebar())}
          className="p-1.5 rounded-md text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors focus:outline-none"
          title="Toggle Navigation Menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="relative hidden md:block w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search Deviations, Batches, CQAs..."
            className="w-full h-9 pl-9 pr-4 text-xs bg-slate-50 border border-slate-300 rounded-md text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-900 focus:bg-white transition-all font-sans"
          />
        </div>
      </div>

      {/* Right: System Telemetry & User Profile */}
      <div className="flex items-center gap-4">
        {/* Backend & DB Health Telemetry Indicators */}
        <div className="hidden lg:flex items-center gap-3 px-3 py-1 bg-slate-50 border border-slate-200 rounded-md font-mono text-[11px]">
          <div className="flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-slate-600">API:</span>
            {backendStatus === 'online' ? (
              <span className="text-emerald-700 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" /> 200 OK
              </span>
            ) : backendStatus === 'checking' ? (
              <span className="text-slate-400">CHECK</span>
            ) : (
              <span className="text-rose-700 font-semibold flex items-center gap-1">
                <AlertCircle className="w-3 h-3 text-rose-600" /> OFFLINE
              </span>
            )}
          </div>

          <div className="w-px h-3.5 bg-slate-300" />

          <div className="flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-slate-600">PostgreSQL:</span>
            {dbStatus === 'connected' ? (
              <span className="text-emerald-700 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" /> READY
              </span>
            ) : dbStatus === 'checking' ? (
              <span className="text-slate-400">CHECK</span>
            ) : (
              <span className="text-amber-700 font-semibold flex items-center gap-1" title="PostgreSQL service awaiting connection or container start">
                STANDBY
              </span>
            )}
          </div>
        </div>

        {/* Notifications */}
        <button className="relative p-2 rounded-md text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-600" />
        </button>

        {/* User Card */}
        <div className="flex items-center gap-3 pl-2 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-slate-900 text-slate-100 flex items-center justify-center font-bold text-xs shadow-xs">
            {user?.fullName?.charAt(0) || 'U'}
          </div>
          <div className="hidden sm:flex flex-col text-left">
            <span className="text-xs font-semibold text-slate-900 leading-tight">
              {user?.fullName || 'Quality Investigator'}
            </span>
            <div className="flex items-center gap-1 text-[10px] text-slate-500">
              <Shield className="w-2.5 h-2.5 text-sky-600" />
              <span>{user?.role?.replace('_', ' ') || 'QA Role'}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
