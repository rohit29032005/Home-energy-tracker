import React, { useState } from 'react';
import { Zap, Server, ChevronDown, Plus, UserPlus, X } from 'lucide-react';
import type { User } from '../types';

interface HeaderProps {
  users: User[];
  currentUser: User | null;
  onSelectUser: (user: User) => void;
  onAddUser?: (user: Partial<User>) => Promise<User>;
  canCreateAccounts: boolean;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  users,
  currentUser,
  onSelectUser,
  onAddUser,
  canCreateAccounts,
  activeTab,
  setActiveTab
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [threshold, setThreshold] = useState<number>(75.0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canCreateAccounts || !name.trim() || !email.trim() || !onAddUser) return;

    setIsSubmitting(true);
    try {
      const created = await onAddUser({
        name,
        email,
        alerting: true,
        energyAlertingThreshold: Number(threshold)
      });
      onSelectUser(created);
      setName('');
      setEmail('');
      setThreshold(75.0);
      setIsModalOpen(false);
    } catch (err) {
      console.error('Failed to create account:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-200 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            
            {/* Logo & Brand */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl gradient-green flex items-center justify-center text-white shadow-md shadow-green-500/20">
                <Zap className="w-6 h-6 fill-current text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-xl text-slate-900 tracking-tight">Home Energy Tracker</span>
                  <span className="bg-green-100 text-green-800 text-xs font-semibold px-2 py-0.5 rounded-full border border-green-200">
                    ⚡ Microservices
                  </span>
                </div>
                <p className="text-xs text-slate-500 hidden sm:block">Kafka • InfluxDB • Standby Energy Detective</p>
              </div>
            </div>

            {/* Navigation Tabs */}
            <nav className="hidden md:flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
              {[
                { id: 'dashboard', label: 'Dashboard' },
                { id: 'devices', label: 'Devices' },
                { id: 'simulator', label: 'Reading Simulator' },
                { id: 'alerts', label: 'Alert History' }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all cursor-pointer ${
                    activeTab === tab.id
                      ? 'bg-white text-slate-900 shadow-xs font-semibold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>

            {/* User Selection Dropdown & Infrastructure Status */}
            <div className="flex items-center gap-3">
              
              {/* System Status Indicator */}
              <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-600">
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <Server className="w-3.5 h-3.5 text-slate-400" />
                <span>Gateway :8080 Active</span>
              </div>

              {/* Active User Switcher */}
              <div className="relative group">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 hover:bg-slate-200/70 cursor-pointer rounded-xl border border-slate-200 transition-colors">
                  <div className="w-7 h-7 rounded-lg bg-emerald-600 text-white flex items-center justify-center font-bold text-xs">
                    {currentUser ? currentUser.name.charAt(0) : 'U'}
                  </div>
                  <div className="text-left hidden sm:block">
                    <div className="text-xs font-bold text-slate-800 leading-tight">
                      {currentUser ? currentUser.name : 'Select User'}
                    </div>
                    <div className="text-[10px] text-slate-500">
                      Threshold: {currentUser?.energyAlertingThreshold || 100} kWh
                    </div>
                  </div>
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                </div>

                {/* Dropdown Menu */}
                <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-lg border border-slate-200 py-1 hidden group-hover:block z-50">
                  <div className="px-3 py-2 border-b border-slate-100 text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                    <span>Household Profiles</span>
                    <span className="text-[10px] bg-slate-100 px-1.5 py-0.5 rounded text-slate-500 font-mono">
                      {users.length} Account{users.length !== 1 ? 's' : ''}
                    </span>
                  </div>

                  <div className="max-h-60 overflow-y-auto">
                    {users.map(u => (
                      <button
                        key={u.id}
                        onClick={() => onSelectUser(u)}
                        className={`w-full text-left px-3 py-2.5 text-xs flex items-center justify-between hover:bg-slate-50 transition-colors cursor-pointer ${
                          currentUser?.id === u.id ? 'bg-emerald-50 text-emerald-900 font-semibold' : 'text-slate-700'
                        }`}
                      >
                        <div>
                          <div className="font-medium">{u.name}</div>
                          <div className="text-[10px] text-slate-400">{u.email}</div>
                          <div className="text-[10px] text-emerald-600 font-mono">Alert Limit: {u.energyAlertingThreshold} kWh</div>
                        </div>
                        {currentUser?.id === u.id && (
                          <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></span>
                        )}
                      </button>
                    ))}
                  </div>

                  {canCreateAccounts && onAddUser && (
                    <div className="p-2 border-t border-slate-100 bg-slate-50/50">
                      <button
                        onClick={() => setIsModalOpen(true)}
                        className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer shadow-xs"
                      >
                        <UserPlus className="w-3.5 h-3.5" />
                        <span>+ Add New Account</span>
                      </button>
                    </div>
                  )}

                </div>
              </div>

            </div>

          </div>
        </div>
      </header>

      {/* Add New Account Modal */}
      {isModalOpen && canCreateAccounts && onAddUser && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-5">
            
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                  <UserPlus className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-slate-900 text-base">Register New Account / Household</h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Household / User Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. John Doe / Eco Smart Villa"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Email Address (for Alert Dispatch)</label>
                <input
                  type="email"
                  required
                  placeholder="e.g. john.doe@example.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Energy Alerting Threshold (kWh)</label>
                <div className="relative">
                  <input
                    type="number"
                    step="5"
                    min="10"
                    max="1000"
                    value={threshold}
                    onChange={e => setThreshold(Number(e.target.value))}
                    className="w-full p-2.5 pr-12 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-bold"
                  />
                  <span className="absolute right-3 top-2.5 font-bold text-slate-400">kWh</span>
                </div>
                <p className="text-[10px] text-slate-400 mt-1">
                  Triggers an automated Kafka alert & email dispatch if consumption exceeds this limit.
                </p>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold transition-colors cursor-pointer disabled:opacity-50 inline-flex items-center gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>{isSubmitting ? 'Creating Account...' : 'Create Account'}</span>
                </button>
              </div>
            </form>

          </div>
        </div>
      )}
    </>
  );
};

