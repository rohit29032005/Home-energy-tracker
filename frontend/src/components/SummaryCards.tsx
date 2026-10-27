import React from 'react';
import { Zap, DollarSign, TrendingUp, Tv, AlertTriangle, ShieldCheck } from 'lucide-react';
import type { BillForecast, ApplianceRankingResult, User } from '../types';

interface SummaryCardsProps {
  forecast: BillForecast | null;
  rankings: ApplianceRankingResult | null;
  currentUser: User | null;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({
  forecast,
  rankings,
  currentUser
}) => {
  const currentKwh = forecast ? forecast.currentKwh : 0;
  const threshold = currentUser ? currentUser.energyAlertingThreshold : 100;
  const isOverThreshold = currentKwh > threshold;
  const topDevice = rankings && rankings.rankings.length > 0 ? rankings.rankings[0] : null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
      
      {/* 1. Total Consumption Card */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs metric-card-hover relative overflow-hidden">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total kWh (3 Days)</span>
          <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <Zap className="w-5 h-5" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">{currentKwh.toFixed(1)}</span>
          <span className="text-sm font-semibold text-slate-500">kWh</span>
        </div>
        <div className="mt-3 flex items-center gap-1.5 text-xs">
          {isOverThreshold ? (
            <span className="flex items-center gap-1 text-red-600 font-semibold bg-red-50 px-2 py-0.5 rounded-md border border-red-100">
              <AlertTriangle className="w-3.5 h-3.5" />
              Above limit ({threshold} kWh)
            </span>
          ) : (
            <span className="flex items-center gap-1 text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">
              <ShieldCheck className="w-3.5 h-3.5" />
              Within threshold ({threshold} kWh)
            </span>
          )}
        </div>
      </div>

      {/* 2. Estimated Current Cost Card */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs metric-card-hover">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Estimated Cost</span>
          <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <DollarSign className="w-5 h-5" />
          </div>
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
            ${forecast ? forecast.currentEstimatedCost.toFixed(2) : '0.00'}
          </span>
          <span className="text-xs font-medium text-slate-400">USD</span>
        </div>
        <p className="mt-3 text-xs text-slate-500 truncate" title={forecast?.tariffSummary || 'Tiered Slabs'}>
          Tiered Slab Rate Applied
        </p>
      </div>

      {/* 3. Month-End Bill Shock Forecast Card */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs metric-card-hover border-l-4 border-l-amber-500">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-amber-700 uppercase tracking-wider">30-Day Bill Forecast</span>
          <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <TrendingUp className="w-5 h-5" />
          </div>
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
            ${forecast ? forecast.projectedMonthlyCost.toFixed(2) : '0.00'}
          </span>
        </div>
        <div className="mt-3 text-xs text-slate-600 flex items-center gap-1 font-medium">
          <span>Projected:</span>
          <span className="font-bold text-slate-800">{forecast ? forecast.projectedMonthlyKwh.toFixed(0) : 0} kWh/mo</span>
          <span className="text-slate-400">({forecast ? forecast.dailyRateKwh.toFixed(1) : 0} kWh/day)</span>
        </div>
      </div>

      {/* 4. Top Appliance Card */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs metric-card-hover">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Top Consuming Appliance</span>
          <div className="w-9 h-9 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
            <Tv className="w-5 h-5" />
          </div>
        </div>
        {topDevice ? (
          <>
            <div className="text-lg font-bold text-slate-900 truncate" title={topDevice.name}>
              {topDevice.name}
            </div>
            <div className="mt-3 flex items-center justify-between text-xs">
              <span className="font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-md">
                {topDevice.energyConsumedKwh.toFixed(1)} kWh ({topDevice.percentageOfTotal.toFixed(0)}%)
              </span>
              <span className="text-slate-500 font-medium">${topDevice.estimatedCost.toFixed(2)}</span>
            </div>
          </>
        ) : (
          <div className="text-sm text-slate-400 italic">No device data available</div>
        )}
      </div>

    </div>
  );
};
