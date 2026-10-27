export interface User {
  id: Long;
  name: string;
  email: string;
  alerting: boolean;
  energyAlertingThreshold: number;
}

export type Long = number;

export interface Device {
  id: number;
  name: string;
  type: string;
  location: string;
  userId: number;
  energyConsumed?: number;
}

export interface IngestionPayload {
  deviceId: number;
  energyConsumed: number;
  timestamp?: string;
}

export interface BillForecast {
  userId: number;
  periodDays: number;
  currentKwh: number;
  currentEstimatedCost: number;
  dailyRateKwh: number;
  projectedMonthlyKwh: number;
  projectedMonthlyCost: number;
  tariffSummary: string;
}

export interface ApplianceRanking {
  deviceId: number;
  name: string;
  type: string;
  location: string;
  energyConsumedKwh: number;
  percentageOfTotal: number;
  estimatedCost: number;
}

export interface ApplianceRankingResult {
  userId: number;
  periodDays: number;
  totalKwh: number;
  totalEstimatedCost: number;
  rankings: ApplianceRanking[];
}

export interface StandbyDetective {
  userId: number;
  baselineWatts: number;
  standbyDailyKwh: number;
  standbyMonthlyKwh: number;
  standbyMonthlyCost: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  recommendations: string[];
  probableCategories: string[];
  baselineAssumptions: string;
}

export interface Alert {
  id: number;
  userId: number;
  message: string;
  threshold: number;
  energyConsumed: number;
  email?: string;
  createdAt: string;
}

export interface Insight {
  userId: number;
  tips: string;
  energyUsage: number;
  estimatedCost: number;
  projectedMonthlyCost: number;
  isAiGenerated: boolean;
  standbyRiskLevel: string;
}

export interface UsageChartData {
  time: string;
  kwh: number;
}
