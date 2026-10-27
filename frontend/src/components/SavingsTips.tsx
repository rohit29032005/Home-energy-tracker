import React from 'react';
import { Lightbulb, Sparkles, ShieldCheck } from 'lucide-react';
import type { Insight } from '../types';

interface SavingsTipsProps {
  insight: Insight | null;
}

export const SavingsTips: React.FC<SavingsTipsProps> = ({ insight }) => {
  if (!insight) return null;

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-4">
      
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
            <Lightbulb className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm">Energy Savings & Bill Intelligence</h3>
            <p className="text-xs text-slate-500">Evidence-based recommendations to reduce electricity costs</p>
          </div>
        </div>

        {/* AI vs Deterministic Fallback Badge */}
        {insight.isAiGenerated ? (
          <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 bg-purple-50 text-purple-700 rounded-lg border border-purple-200">
            <Sparkles className="w-3.5 h-3.5" />
            AI Generated
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 bg-slate-100 text-slate-700 rounded-lg border border-slate-200">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            Deterministic Analytics
          </span>
        )}
      </div>

      <div className="text-xs text-slate-700 leading-relaxed whitespace-pre-line bg-slate-50 p-4 rounded-xl border border-slate-200/80">
        {insight.tips}
      </div>

    </div>
  );
};
