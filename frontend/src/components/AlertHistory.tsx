import React from 'react';
import { AlertTriangle, Mail, Clock, ShieldAlert } from 'lucide-react';
import type { Alert, User } from '../types';

interface AlertHistoryProps {
  alerts: Alert[];
  currentUser: User | null;
}

export const AlertHistory: React.FC<AlertHistoryProps> = ({ alerts, currentUser }) => {
  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">Household Alert History</h2>
            <p className="text-xs text-slate-500">Recorded energy threshold breaches and automated notification logs (<code className="text-red-600 font-mono">energy-alerts</code> topic)</p>
          </div>
        </div>

        <span className="text-xs font-semibold px-2.5 py-1 bg-red-50 text-red-700 rounded-lg border border-red-100">
          {alerts.length} Alert Event{alerts.length === 1 ? '' : 's'}
        </span>
      </div>

      {/* Alerts List */}
      <div className="space-y-3">
        {alerts.map(alert => (
          <div
            key={alert.id}
            className="p-4 bg-red-50/50 rounded-xl border border-red-200/70 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
          >
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-red-100 text-red-600 flex items-center justify-center shrink-0 mt-0.5">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-red-950">{alert.message}</h4>
                <div className="mt-1 flex items-center gap-3 text-[11px] text-slate-600">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    {alert.createdAt}
                  </span>
                  <span className="flex items-center gap-1 text-slate-500">
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    Sent to: {alert.email || currentUser?.email || 'user@example.com'}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 self-end sm:self-center">
              <div className="text-right">
                <div className="text-xs font-bold text-red-700">{alert.energyConsumed.toFixed(1)} kWh</div>
                <div className="text-[10px] text-slate-400">Limit: {alert.threshold} kWh</div>
              </div>
            </div>
          </div>
        ))}

        {alerts.length === 0 && (
          <div className="py-12 text-center bg-slate-50 rounded-xl border border-dashed border-slate-300">
            <ShieldAlert className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
            <p className="text-sm font-medium text-slate-700">No energy threshold breaches detected!</p>
            <p className="text-xs text-slate-400 mt-1">Your household consumption remains safely within your configured threshold ({currentUser?.energyAlertingThreshold || 100} kWh).</p>
          </div>
        )}
      </div>

    </div>
  );
};
