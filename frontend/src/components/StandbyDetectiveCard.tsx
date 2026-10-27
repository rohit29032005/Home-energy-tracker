import React, { useState } from 'react';
import { Ghost, AlertCircle, CheckCircle2, Info } from 'lucide-react';
import type { StandbyDetective } from '../types';

interface StandbyDetectiveCardProps {
  standby: StandbyDetective | null;
}

export const StandbyDetectiveCard: React.FC<StandbyDetectiveCardProps> = ({ standby }) => {
  const [completedTips, setCompletedTips] = useState<Record<number, boolean>>({});

  if (!standby) return null;

  const toggleTip = (idx: number) => {
    setCompletedTips(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const getRiskBadge = (level: string) => {
    switch (level) {
      case 'HIGH':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'MEDIUM':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      default:
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    }
  };

  return (
    <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden">
      
      {/* Decorative Glow Elements */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/10 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none"></div>
      
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
        
        {/* Left Info Column */}
        <div className="space-y-4 max-w-xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <Ghost className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-white tracking-tight">Standby Energy Detective</h3>
                <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${getRiskBadge(standby.riskLevel)}`}>
                  {standby.riskLevel} RISK
                </span>
              </div>
              <p className="text-xs text-slate-400">Detecting continuous phantom (idle) load during low-activity hours</p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 bg-slate-800/80 p-3.5 rounded-xl border border-slate-700/60 text-center">
            <div>
              <div className="text-[10px] uppercase font-semibold text-slate-400">Baseline Load</div>
              <div className="text-xl font-extrabold text-amber-400 mt-0.5">{standby.baselineWatts.toFixed(0)} W</div>
            </div>
            <div className="border-x border-slate-700/60">
              <div className="text-[10px] uppercase font-semibold text-slate-400">Monthly Wastage</div>
              <div className="text-xl font-extrabold text-white mt-0.5">{standby.standbyMonthlyKwh.toFixed(1)} <span className="text-xs font-normal">kWh</span></div>
            </div>
            <div>
              <div className="text-[10px] uppercase font-semibold text-slate-400">Phantom Cost</div>
              <div className="text-xl font-extrabold text-emerald-400 mt-0.5">${standby.standbyMonthlyCost.toFixed(2)}</div>
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-[11px] text-slate-400 bg-slate-800/40 px-3 py-1.5 rounded-lg border border-slate-700/40">
            <Info className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span className="truncate">{standby.baselineAssumptions}</span>
          </div>
        </div>

        {/* Right Recommendation Checklist */}
        <div className="bg-slate-800/90 rounded-xl p-4 border border-slate-700/80 lg:w-96 flex-shrink-0">
          <div className="flex items-center justify-between mb-3 border-b border-slate-700/60 pb-2">
            <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4 text-amber-400" />
              Actionable Saving Checklist
            </span>
            <span className="text-[10px] text-slate-400">Click to complete</span>
          </div>

          <ul className="space-y-2 text-xs">
            {standby.recommendations.map((rec, idx) => {
              const done = !!completedTips[idx];
              return (
                <li
                  key={idx}
                  onClick={() => toggleTip(idx)}
                  className={`flex items-start gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
                    done ? 'bg-emerald-950/40 text-emerald-300 line-through opacity-70' : 'hover:bg-slate-700/50 text-slate-300'
                  }`}
                >
                  <CheckCircle2 className={`w-4 h-4 shrink-0 mt-0.5 ${done ? 'text-emerald-400 fill-emerald-950' : 'text-slate-500'}`} />
                  <span>{rec}</span>
                </li>
              );
            })}
          </ul>

          <div className="mt-3 pt-2 border-t border-slate-700/60 text-[11px] text-slate-400">
            <span className="font-semibold text-slate-300">Suspect Devices: </span>
            {standby.probableCategories.slice(0, 2).join(', ')}
          </div>
        </div>

      </div>

    </div>
  );
};
