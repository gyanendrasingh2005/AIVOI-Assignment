import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  AlertOctagon, 
  FolderGit2, 
  GitFork, 
  CheckSquare, 
  ShieldCheck,
  Building2,
  FileSpreadsheet
} from 'lucide-react';
import { clsx } from 'clsx';
import { useAppSelector } from '@/store/hooks';

interface SidebarProps {
  className?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ className }) => {
  const { sidebarOpen } = useAppSelector((state) => state.ui);

  const navItems = [
    {
      name: 'Quality Dashboard',
      path: '/dashboard',
      icon: LayoutDashboard,
      badge: undefined,
    },
    {
      name: 'Investigations',
      path: '/investigations',
      icon: AlertOctagon,
      badge: '3 Open',
    },
    {
      name: 'Evidence Repository',
      path: '/evidence',
      icon: FolderGit2,
      badge: undefined,
    },
    {
      name: 'BPR & Documents',
      path: '/documents',
      icon: FileSpreadsheet,
      badge: undefined,
    },
    {
      name: 'RCA Workspace',
      path: '/rca',
      icon: GitFork,
      badge: 'AI Active',
    },
    {
      name: 'CAPA Management',
      path: '/capa',
      icon: CheckSquare,
      badge: undefined,
    },
    {
      name: 'QA Approvals',
      path: '/approvals',
      icon: ShieldCheck,
      badge: '2 Pending',
    },
  ];

  return (
    <aside
      className={clsx(
        'bg-slate-900 text-slate-300 flex flex-col border-r border-slate-800 transition-all duration-200 z-30 select-none',
        sidebarOpen ? 'w-64' : 'w-20',
        className
      )}
    >
      {/* Brand Header */}
      <div className="h-16 px-4 flex items-center gap-3 border-b border-slate-800 bg-slate-950/40">
        <div className="w-9 h-9 rounded-lg bg-sky-700 text-white flex items-center justify-center font-bold tracking-wider shadow-sm shrink-0 border border-sky-600/50">
          PR
        </div>
        {sidebarOpen && (
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold tracking-wide text-white truncate font-sans">
              PharmaRCA
            </span>
            <span className="text-[10px] tracking-wider text-slate-400 uppercase font-mono truncate">
              API Manufacturing QMS
            </span>
          </div>
        )}
      </div>

      {/* Facility Badge */}
      {sidebarOpen && (
        <div className="px-4 py-2.5 mx-3 my-3 rounded-md bg-slate-800/60 border border-slate-700/60 flex items-center gap-2">
          <Building2 className="w-4 h-4 text-sky-400 shrink-0" />
          <div className="flex flex-col min-w-0 text-left">
            <span className="text-[11px] font-semibold text-slate-200 truncate">Site 04 - API Sterile Synthesis</span>
            <span className="text-[9px] font-mono text-slate-400 uppercase">GMP Zone Class C/D</span>
          </div>
        </div>
      )}

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-md text-xs font-medium transition-colors group relative',
                  isActive
                    ? 'bg-sky-900/60 text-white border border-sky-700/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/70'
                )
              }
            >
              <Icon className="w-4 h-4 shrink-0 transition-transform group-hover:scale-105" />
              {sidebarOpen && (
                <div className="flex items-center justify-between flex-1 min-w-0">
                  <span className="truncate">{item.name}</span>
                  {item.badge && (
                    <span
                      className={clsx(
                        'text-[10px] px-1.5 py-0.5 rounded font-mono font-medium ml-2',
                        item.badge.includes('AI')
                          ? 'bg-sky-500/20 text-sky-300 border border-sky-400/30'
                          : item.badge.includes('Pending')
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-400/30'
                          : 'bg-slate-700 text-slate-300'
                      )}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Compliance / 21 CFR Part 11 Footer */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/30 text-center">
        {sidebarOpen ? (
          <div className="text-[10px] text-slate-400 space-y-1">
            <div className="flex items-center justify-center gap-1.5 font-mono text-[9px] text-sky-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              21 CFR PART 11 COMPLIANT
            </div>
            <div className="text-slate-500 text-[9px]">Audit Engine Active v1.0.0</div>
          </div>
        ) : (
          <div className="flex justify-center">
            <span className="w-2 h-2 rounded-full bg-emerald-400" title="21 CFR Part 11 Active" />
          </div>
        )}
      </div>
    </aside>
  );
};
