import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Cell
} from 'recharts';
import type { UsageChartData, ApplianceRankingResult } from '../types';

interface UsageChartsProps {
  chartData: UsageChartData[];
  rankings: ApplianceRankingResult | null;
}

const BAR_COLORS = ['#16A34A', '#2563EB', '#D97706', '#9333EA', '#0891B2', '#E11D48'];

export const UsageCharts: React.FC<UsageChartsProps> = ({ chartData, rankings }) => {
  const rankingList = rankings ? rankings.rankings : [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      
      {/* 1. Energy Consumption Line / Area Chart */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-bold text-slate-900 text-base">Household Usage Trend</h3>
            <p className="text-xs text-slate-500">Daily energy consumption (kWh)</p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 text-slate-700 rounded-lg border border-slate-200">
            Past 7 Days
          </span>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorKwh" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#16A34A" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#16A34A" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
              <XAxis dataKey="time" tick={{ fontSize: 12, fill: '#64748B' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: '#64748B' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0F172A', color: '#fff', borderRadius: '12px', border: 'none' }}
                labelStyle={{ color: '#94A3B8', fontWeight: 'bold' }}
                formatter={(value: any) => [`${value} kWh`, 'Consumption']}
              />
              <Area type="monotone" dataKey="kwh" stroke="#16A34A" strokeWidth={3} fillOpacity={1} fill="url(#colorKwh)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. Appliance Consumption Ranking Bar Chart */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-bold text-slate-900 text-base">Appliance Energy Ranking</h3>
            <p className="text-xs text-slate-500">Consumption per registered appliance (kWh)</p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-purple-50 text-purple-700 rounded-lg border border-purple-100">
            Top Consumers
          </span>
        </div>

        <div className="h-64 w-full">
          {rankingList.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rankingList} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
                <XAxis type="number" tick={{ fontSize: 12, fill: '#64748B' }} axisLine={false} tickLine={false} />
                <YAxis dataKey="name" type="category" width={110} tick={{ fontSize: 11, fill: '#334155', fontWeight: 600 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0F172A', color: '#fff', borderRadius: '12px', border: 'none' }}
                  formatter={(value: any) => [`${value} kWh`, 'Energy Used']}
                />
                <Bar dataKey="energyConsumedKwh" radius={[0, 8, 8, 0]} barSize={20}>
                  {rankingList.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-400 text-sm italic">
              No registered appliances found.
            </div>
          )}
        </div>
      </div>

    </div>
  );
};
