import type {
  User,
  Device,
  IngestionPayload,
  BillForecast,
  ApplianceRankingResult,
  StandbyDetective,
  Alert,
  Insight,
  UsageChartData
} from '../types';
import { auth } from './auth';

const API_BASE = '/api/v1';

// Initial Demo State for local fallback & rich immediate rendering
export const DEMO_USERS: User[] = [
  { id: 1, name: 'Alex Johnson', email: 'alex.j@example.com', alerting: true, energyAlertingThreshold: 75.0 },
  { id: 2, name: 'Sarah Miller', email: 'sarah.m@example.com', alerting: true, energyAlertingThreshold: 120.0 },
  { id: 3, name: 'Demo Household', email: 'demo@hometracker.io', alerting: true, energyAlertingThreshold: 50.0 }
];

export const DEMO_DEVICES: Record<number, Device[]> = {
  1: [
    { id: 101, name: 'Smart Air Conditioner', type: 'HVAC', location: 'Master Bedroom', userId: 1, energyConsumed: 48.5 },
    { id: 102, name: 'Double Door Refrigerator', type: 'Kitchen', location: 'Kitchen', userId: 1, energyConsumed: 22.1 },
    { id: 103, name: 'Gaming Desktop PC', type: 'Office', location: 'Study Room', userId: 1, energyConsumed: 18.4 },
    { id: 104, name: '4K OLED TV & Soundbar', type: 'Entertainment', location: 'Living Room', userId: 1, energyConsumed: 12.8 },
    { id: 105, name: 'Induction Cooktop', type: 'Kitchen', location: 'Kitchen', userId: 1, energyConsumed: 9.6 }
  ],
  2: [
    { id: 201, name: 'Central HVAC System', type: 'HVAC', location: 'Whole House', userId: 2, energyConsumed: 85.0 },
    { id: 202, name: 'Electric Water Heater', type: 'Utility', location: 'Basement', userId: 2, energyConsumed: 38.2 },
    { id: 203, name: 'Kitchen Fridge', type: 'Kitchen', location: 'Kitchen', userId: 2, energyConsumed: 19.5 }
  ],
  3: [
    { id: 301, name: 'Studio Mini Fridge', type: 'Kitchen', location: 'Kitchen', userId: 3, energyConsumed: 14.0 },
    { id: 302, name: 'Workstation Laptop', type: 'Office', location: 'Desk', userId: 3, energyConsumed: 8.5 }
  ]
};

export const DEMO_ALERTS: Record<number, Alert[]> = {
  1: [
    { id: 501, userId: 1, message: 'Energy threshold exceeded: 111.4 kWh (Limit: 75.0 kWh)', threshold: 75.0, energyConsumed: 111.4, email: 'alex.j@example.com', createdAt: '2026-09-09 20:15:00' },
    { id: 502, userId: 1, message: 'High evening peak consumption detected', threshold: 75.0, energyConsumed: 82.3, email: 'alex.j@example.com', createdAt: '2026-09-08 19:30:00' }
  ],
  2: [
    { id: 503, userId: 2, message: 'Energy threshold exceeded: 142.7 kWh (Limit: 120.0 kWh)', threshold: 120.0, energyConsumed: 142.7, email: 'sarah.m@example.com', createdAt: '2026-09-09 18:45:00' }
  ],
  3: []
};

// Helper for fetch with JSON response
async function fetchJson<T>(url: string, options?: RequestInit, fallback?: T): Promise<T> {
  try {
    const res = await auth.fetchWithAuth(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Correlation-ID': `web-${Date.now()}`,
        ...(options?.headers || {})
      }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    if (auth.enabled) throw err;
    if (fallback !== undefined) {
      console.warn(`[API Gateway] Request to ${url} failed or offline. Using local fallback data.`, err);
      return fallback;
    }
    throw err;
  }
}

export const api = {
  // Users
  getUsers: async (): Promise<User[]> => {
    return fetchJson<User[]>(`${API_BASE}/user`, {}, DEMO_USERS);
  },

  getUserById: async (userId: number): Promise<User> => {
    const fallback = DEMO_USERS.find(u => u.id === userId) || DEMO_USERS[0];
    return fetchJson<User>(`${API_BASE}/user/${userId}`, {}, fallback);
  },

  createUser: async (user: Partial<User>): Promise<User> => {
    const newUser: User = {
      id: Date.now(),
      name: user.name || 'New User',
      email: user.email || 'user@example.com',
      alerting: user.alerting ?? true,
      energyAlertingThreshold: user.energyAlertingThreshold || 100.0
    };
    return fetchJson<User>(`${API_BASE}/user`, {
      method: 'POST',
      body: JSON.stringify(user)
    }, newUser);
  },

  // Devices
  getDevicesByUser: async (userId: number): Promise<Device[]> => {
    const fallback = DEMO_DEVICES[userId] || DEMO_DEVICES[1];
    return fetchJson<Device[]>(`${API_BASE}/device/user/${userId}`, {}, fallback);
  },

  createDevice: async (device: Partial<Device>): Promise<Device> => {
    const userId = device.userId || 1;
    const newDevice: Device = {
      id: Date.now(),
      name: device.name || 'New Appliance',
      type: device.type || 'General',
      location: device.location || 'Living Room',
      userId: userId,
      energyConsumed: 0.0
    };

    try {
      const res = await auth.fetchWithAuth(`${API_BASE}/device`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(device)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const created = await res.json();
      if (!DEMO_DEVICES[userId]) DEMO_DEVICES[userId] = [];
      DEMO_DEVICES[userId].push(created);
      return created;
    } catch (error) {
      if (auth.enabled) throw error;
      console.warn(`[API] Create device fallback executed.`);
      if (!DEMO_DEVICES[userId]) DEMO_DEVICES[userId] = [];
      DEMO_DEVICES[userId].push(newDevice);
      return newDevice;
    }
  },

  deleteDevice: async (deviceId: number): Promise<void> => {
    try {
      const response = await auth.fetchWithAuth(`${API_BASE}/device/${deviceId}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
    } catch (error) {
      if (auth.enabled) throw error;
      console.warn(`[API] Delete device ${deviceId} fallback executed.`);
    }
    Object.keys(DEMO_DEVICES).forEach(uid => {
      const numUid = Number(uid);
      DEMO_DEVICES[numUid] = DEMO_DEVICES[numUid].filter(d => d.id !== deviceId);
    });
  },

  // Ingestion Simulator
  ingestReading: async (payload: IngestionPayload): Promise<{ success: boolean; message: string }> => {
    try {
      const res = await auth.fetchWithAuth(`${API_BASE}/ingestion`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      if (res.ok || res.status === 201) {
        return { success: true, message: 'Reading ingested & emitted to Kafka topic (energy-usage)' };
      }
      if (auth.enabled) throw new Error(`HTTP ${res.status}`);
      return { success: true, message: 'Simulated reading processed locally.' };
    } catch (error) {
      if (auth.enabled) throw error;
      return { success: true, message: 'Simulated reading processed locally (Kafka offline demo).' };
    }
  },

  // Energy Intelligence Insights
  getBillForecast: async (userId: number, days = 3): Promise<BillForecast> => {
    const devices = DEMO_DEVICES[userId] || DEMO_DEVICES[1];
    const totalKwh = devices.reduce((sum, d) => sum + (d.energyConsumed || 0), 0);
    const dailyRate = Math.round((totalKwh / days) * 100) / 100;
    const projectedKwh = Math.round(dailyRate * 30 * 100) / 100;

    const fallback: BillForecast = {
      userId,
      periodDays: days,
      currentKwh: Math.round(totalKwh * 100) / 100,
      currentEstimatedCost: Math.round((totalKwh * 0.18 + 10.00) * 100) / 100,
      dailyRateKwh: dailyRate,
      projectedMonthlyKwh: projectedKwh,
      projectedMonthlyCost: Math.round((projectedKwh * 0.22 + 10.00) * 100) / 100,
      tariffSummary: 'Fixed: $10.00/mo | Slab 1 (0-100kWh): $0.12/kWh | Slab 2 (101-300kWh): $0.18/kWh | Slab 3 (>300kWh): $0.25/kWh'
    };

    return fetchJson<BillForecast>(`${API_BASE}/insight/bill-forecast/${userId}?days=${days}`, {}, fallback);
  },

  getApplianceRanking: async (userId: number, days = 3): Promise<ApplianceRankingResult> => {
    const devices = DEMO_DEVICES[userId] || DEMO_DEVICES[1];
    const totalKwh = devices.reduce((sum, d) => sum + (d.energyConsumed || 0), 0);
    const sorted = [...devices].sort((a, b) => (b.energyConsumed || 0) - (a.energyConsumed || 0));

    const rankings = sorted.map(d => {
      const kwh = d.energyConsumed || 0;
      const pct = totalKwh > 0 ? Math.round((kwh / totalKwh) * 1000) / 10 : 0;
      const cost = Math.round((kwh * 0.18) * 100) / 100;
      return {
        deviceId: d.id,
        name: d.name,
        type: d.type,
        location: d.location,
        energyConsumedKwh: kwh,
        percentageOfTotal: pct,
        estimatedCost: cost
      };
    });

    const fallback: ApplianceRankingResult = {
      userId,
      periodDays: days,
      totalKwh: Math.round(totalKwh * 100) / 100,
      totalEstimatedCost: Math.round((totalKwh * 0.18) * 100) / 100,
      rankings
    };

    return fetchJson<ApplianceRankingResult>(`${API_BASE}/insight/appliance-ranking/${userId}?days=${days}`, {}, fallback);
  },

  getStandbyDetective: async (userId: number, days = 3): Promise<StandbyDetective> => {
    const devices = DEMO_DEVICES[userId] || DEMO_DEVICES[1];
    const totalKwh = devices.reduce((sum, d) => sum + (d.energyConsumed || 0), 0);
    const avgWatts = ((totalKwh / (days * 24)) * 1000) * 0.20;
    const baselineWatts = Math.round(avgWatts * 10) / 10;
    const standbyDailyKwh = Math.round(((baselineWatts * 24) / 1000) * 100) / 100;
    const standbyMonthlyKwh = Math.round(standbyDailyKwh * 30 * 100) / 100;

    const fallback: StandbyDetective = {
      userId,
      baselineWatts,
      standbyDailyKwh,
      standbyMonthlyKwh,
      standbyMonthlyCost: Math.round(standbyMonthlyKwh * 0.18 * 100) / 100,
      riskLevel: baselineWatts > 150 ? 'HIGH' : (baselineWatts > 50 ? 'MEDIUM' : 'LOW'),
      recommendations: [
        'Plug entertainment systems & soundbars into smart surge protectors.',
        'Unplug idle gaming consoles and desktop workstations when not in use.',
        'Check continuous water dispensers and set automated sleep timers.'
      ],
      probableCategories: [
        'Entertainment Systems (TVs, Gaming Consoles, Audio)',
        'Home Office Setup (Desktop PCs, Printers, Monitors)',
        'Kitchen Appliances with Digital Clocks & Idle Chargers'
      ],
      baselineAssumptions: `Baseline load estimated as ~20% continuous idle power during 1:00 AM - 5:00 AM low-activity windows over ${days} days.`
    };

    return fetchJson<StandbyDetective>(`${API_BASE}/insight/standby-detective/${userId}?days=${days}`, {}, fallback);
  },

  getSavingTips: async (userId: number): Promise<Insight> => {
    const devices = DEMO_DEVICES[userId] || DEMO_DEVICES[1];
    const totalKwh = devices.reduce((sum, d) => sum + (d.energyConsumed || 0), 0);

    const fallback: Insight = {
      userId,
      tips: `💡 **Energy Saving Recommendations**\n\n1. **Top Consumer:** Shift heavy HVAC/Air Conditioner operation to off-peak hours.\n2. **Standby Load:** Eliminate 78W phantom idle load to save ~$10.20/month.\n3. **Tariff Optimization:** Stay under the 100 kWh baseline slab to maintain $0.12/kWh pricing.`,
      energyUsage: Math.round(totalKwh * 100) / 100,
      estimatedCost: Math.round((totalKwh * 0.18) * 100) / 100,
      projectedMonthlyCost: Math.round((totalKwh * 3.5 * 0.18) * 100) / 100,
      isAiGenerated: false,
      standbyRiskLevel: 'MEDIUM'
    };

    return fetchJson<Insight>(`${API_BASE}/insight/saving-tips/${userId}`, {}, fallback);
  },

  // Alerts
  getAlertsByUser: async (userId: number): Promise<Alert[]> => {
    const fallback = DEMO_ALERTS[userId] || [];
    return fetchJson<Alert[]>(`${API_BASE}/alert/user/${userId}`, {}, fallback);
  },

  // Usage History Chart Generator
  getUsageChartData: async (userId: number, days = 7): Promise<UsageChartData[]> => {
    const devices = DEMO_DEVICES[userId] || DEMO_DEVICES[1];
    const totalKwh = devices.reduce((sum, d) => sum + (d.energyConsumed || 0), 0);
    const avgDaily = totalKwh / days || 12.5;

    const data: UsageChartData[] = [];
    const now = new Date();
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(now.getDate() - i);
      const randomFactor = 0.75 + Math.random() * 0.5;
      data.push({
        time: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        kwh: Math.round(avgDaily * randomFactor * 10) / 10
      });
    }
    return data;
  }
};
