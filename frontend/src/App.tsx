import { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { SummaryCards } from './components/SummaryCards';
import { StandbyDetectiveCard } from './components/StandbyDetectiveCard';
import { UsageCharts } from './components/UsageCharts';
import { DeviceManagement } from './components/DeviceManagement';
import { SimulatorControls } from './components/SimulatorControls';
import { AlertHistory } from './components/AlertHistory';
import { SavingsTips } from './components/SavingsTips';

import { api } from './services/api';
import { auth } from './services/auth';
import type {
  User,
  Device,
  BillForecast,
  ApplianceRankingResult,
  StandbyDetective,
  Alert,
  Insight,
  UsageChartData,
  IngestionPayload
} from './types';

export function App() {
  const [users, setUsers] = useState<User[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<string>('dashboard');

  const [devices, setDevices] = useState<Device[]>([]);
  const [forecast, setForecast] = useState<BillForecast | null>(null);
  const [rankings, setRankings] = useState<ApplianceRankingResult | null>(null);
  const [standby, setStandby] = useState<StandbyDetective | null>(null);
  const [insight, setInsight] = useState<Insight | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [chartData, setChartData] = useState<UsageChartData[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [authReady, setAuthReady] = useState<boolean>(!auth.enabled);
  const [authenticated, setAuthenticated] = useState<boolean>(!auth.enabled);
  const [authError, setAuthError] = useState<string | null>(null);
  const canCreateAccounts = !auth.enabled || auth.isAdmin();

  useEffect(() => {
    if (!auth.enabled) return;
    auth.completeLogin()
      .then(isAuthenticated => {
        setAuthenticated(isAuthenticated);
        if (!isAuthenticated) setLoading(false);
      })
      .catch(error => {
        setAuthError(error instanceof Error ? error.message : 'Keycloak login failed.');
        setAuthenticated(false);
        setLoading(false);
      })
      .finally(() => setAuthReady(true));
  }, []);

  // Initial Load Users
  useEffect(() => {
    if (!authReady || (auth.enabled && !authenticated)) return;
    const loadProfiles = async () => {
      if (auth.enabled && !auth.isAdmin()) {
        const userId = auth.getHomeEnergyUserId();
        if (!userId) throw new Error('The Keycloak token has no home_energy_user_id ownership claim.');
        const profile = await api.getUserById(userId);
        setUsers([profile]);
        setCurrentUser(profile);
        return;
      }
      const loadedUsers = await api.getUsers();
      setUsers(loadedUsers);
      if (loadedUsers.length > 0) setCurrentUser(loadedUsers[0]);
    };
    loadProfiles().catch(error => {
      console.error('Failed to load authenticated profile:', error);
      setAuthError(error instanceof Error ? error.message : 'Unable to load the authenticated profile.');
      setLoading(false);
    });
  }, [authReady, authenticated]);

  // Load Household Data whenever currentUser changes
  const loadUserData = useCallback(async (userId: number) => {
    try {
      const [
        loadedDevices,
        loadedForecast,
        loadedRankings,
        loadedStandby,
        loadedInsight,
        loadedAlerts,
        loadedChart
      ] = await Promise.all([
        api.getDevicesByUser(userId),
        api.getBillForecast(userId, 3),
        api.getApplianceRanking(userId, 3),
        api.getStandbyDetective(userId, 3),
        api.getSavingTips(userId),
        api.getAlertsByUser(userId),
        api.getUsageChartData(userId, 7)
      ]);

      setDevices(loadedDevices);
      setForecast(loadedForecast);
      setRankings(loadedRankings);
      setStandby(loadedStandby);
      setInsight(loadedInsight);
      setAlerts(loadedAlerts);
      setChartData(loadedChart);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (currentUser) {
      // oxlint-disable-next-line react/set-state-in-effect -- the request settles asynchronously and updates loading/data state.
      loadUserData(currentUser.id);
    }
  }, [currentUser, loadUserData]);

  const handleSelectUser = (user: User) => {
    setLoading(true);
    setCurrentUser(user);
  };

  const handleAddUser = async (userData: Partial<User>): Promise<User> => {
    if (!canCreateAccounts) {
      throw new Error('Only an administrator can create a household account.');
    }
    const createdUser = await api.createUser(userData);
    setUsers(prev => {
      if (prev.some(u => u.id === createdUser.id)) return prev;
      return [...prev, createdUser];
    });
    return createdUser;
  };

  const handleAddDevice = async (deviceData: Partial<Device>) => {
    try {
      const newDevice = await api.createDevice(deviceData);
      setDevices(prev => {
        if (prev.some(d => d.id === newDevice.id)) return prev;
        return [...prev, newDevice];
      });
    } catch (err) {
      console.error('Failed to create device:', err);
    }
  };

  const handleDeleteDevice = async (deviceId: number) => {
    try {
      await api.deleteDevice(deviceId);
      setDevices(prev => prev.filter(d => d.id !== deviceId));
    } catch (err) {
      console.error('Failed to delete device:', err);
    }
  };

  const handleIngestReading = async (payload: IngestionPayload) => {
    const result = await api.ingestReading(payload);
    if (currentUser) {
      setLoading(true);
      loadUserData(currentUser.id);
    }
    return result;
  };

  if (auth.enabled && !authReady) {
    return <div className="min-h-screen grid place-items-center bg-slate-50 text-slate-700">Checking Keycloak session…</div>;
  }

  if (auth.enabled && !authenticated) {
    return (
      <main className="min-h-screen grid place-items-center bg-slate-50 p-6">
        <section className="max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm text-center space-y-4">
          <h1 className="text-2xl font-bold text-slate-800">Home Energy Tracker</h1>
          <p className="text-sm text-slate-600">Sign in through Keycloak to access only the household resources assigned to your account.</p>
          {authError && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{authError}</p>}
          <button className="rounded bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-700" onClick={() => void auth.beginLogin()}>
            Sign in with Keycloak
          </button>
        </section>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      
      {/* Header */}
      <Header
        users={users}
        currentUser={currentUser}
        onSelectUser={handleSelectUser}
        onAddUser={handleAddUser}
        canCreateAccounts={canCreateAccounts}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      {/* Main Dashboard Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 space-y-4">
            <div className="w-12 h-12 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin"></div>
            <p className="text-sm font-semibold text-slate-500">Loading household energy metrics...</p>
          </div>
        ) : (
          <>
            {/* Dashboard View */}
            {activeTab === 'dashboard' && (
              <>
                {/* 1. Summary Cards */}
                <SummaryCards
                  forecast={forecast}
                  rankings={rankings}
                  currentUser={currentUser}
                />

                {/* 2. Standby Energy Detective Novel Feature */}
                <StandbyDetectiveCard standby={standby} />

                {/* 3. Usage Charts */}
                <UsageCharts chartData={chartData} rankings={rankings} />

                {/* 4. AI & Deterministic Savings Tips */}
                <SavingsTips insight={insight} />
              </>
            )}

            {/* Devices View */}
            {activeTab === 'devices' && (
              <DeviceManagement
                devices={devices}
                currentUser={currentUser}
                onAddDevice={handleAddDevice}
                onDeleteDevice={handleDeleteDevice}
              />
            )}

            {/* Reading Simulator View */}
            {activeTab === 'simulator' && (
              <SimulatorControls
                devices={devices}
                onIngest={handleIngestReading}
                onRefreshData={() => currentUser && loadUserData(currentUser.id)}
              />
            )}

            {/* Alert History View */}
            {activeTab === 'alerts' && (
              <AlertHistory alerts={alerts} currentUser={currentUser} />
            )}
          </>
        )}

      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 text-center text-xs text-slate-500">
          <p className="font-semibold text-slate-700">Home Energy Tracker ⚡ Cloud Microservices Architecture</p>
          <p className="mt-1">Spring Cloud Gateway • Kafka Event Ingestion • InfluxDB Time-Series • Standby Energy Detective</p>
        </div>
      </footer>

    </div>
  );
}

export default App;
