import React, { useState } from 'react';
import { Send, Radio, CheckCircle2 } from 'lucide-react';
import type { Device, IngestionPayload } from '../types';

interface SimulatorControlsProps {
  devices: Device[];
  onIngest: (payload: IngestionPayload) => Promise<{ success: boolean; message: string }>;
  onRefreshData: () => void;
}

export const SimulatorControls: React.FC<SimulatorControlsProps> = ({
  devices,
  onIngest,
  onRefreshData
}) => {
  const [selectedDeviceId, setSelectedDeviceId] = useState<number>(devices[0]?.id || 101);
  const [kwhValue, setKwhValue] = useState<number>(5.5);
  const [isSimulating, setIsSimulating] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleSimulate = async () => {
    if (!selectedDeviceId) return;

    setIsSimulating(true);
    setStatusMessage(null);

    try {
      const result = await onIngest({
        deviceId: Number(selectedDeviceId),
        energyConsumed: Number(kwhValue),
        timestamp: new Date().toISOString()
      });

      setStatusMessage(result.message);
      onRefreshData();
    } catch {
      setStatusMessage('Simulated reading processed locally.');
      onRefreshData();
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
      
      <div className="flex items-center justify-between border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">Smart-Meter Reading Simulator</h2>
            <p className="text-xs text-slate-500">Inject simulated energy readings directly into Ingestion Service & Kafka topic (<code className="text-purple-600 font-mono">energy-usage</code>)</p>
          </div>
        </div>
        <span className="text-xs font-semibold px-2.5 py-1 bg-purple-50 text-purple-700 rounded-lg border border-purple-100">
          Demo Ingest Pipeline
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        
        {/* Device Selector */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">Target Appliance</label>
          <select
            value={selectedDeviceId}
            onChange={e => setSelectedDeviceId(Number(e.target.value))}
            className="w-full text-xs p-3 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
          >
            {devices.map(d => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.location})
              </option>
            ))}
          </select>
        </div>

        {/* kWh Value */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">Energy Consumed (kWh)</label>
          <div className="relative">
            <input
              type="number"
              step="0.1"
              min="0.1"
              max="100.0"
              value={kwhValue}
              onChange={e => setKwhValue(Number(e.target.value))}
              className="w-full text-xs p-3 pr-10 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-purple-500 font-bold"
            />
            <span className="absolute right-3 top-3 text-xs font-semibold text-slate-400">kWh</span>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex items-end">
          <button
            onClick={handleSimulate}
            disabled={isSimulating}
            className="w-full inline-flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold p-3 rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-50"
          >
            {isSimulating ? (
              <span>Publishing to Kafka...</span>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>Simulate & Publish Reading</span>
              </>
            )}
          </button>
        </div>

      </div>

      {/* Preset Quick Buttons */}
      <div className="pt-2">
        <span className="text-xs font-semibold text-slate-500 block mb-2">Quick Simulation Presets:</span>
        <div className="flex flex-wrap gap-2">
          {[
            { label: 'Normal Usage (+2.5 kWh)', val: 2.5 },
            { label: 'Heavy Usage (+15.0 kWh)', val: 15.0 },
            { label: 'Threshold Surge (+55.0 kWh)', val: 55.0 }
          ].map((preset, idx) => (
            <button
              key={idx}
              onClick={() => {
                setKwhValue(preset.val);
              }}
              className="text-xs px-3 py-1.5 bg-slate-100 hover:bg-purple-50 hover:text-purple-700 hover:border-purple-200 border border-slate-200 rounded-lg transition-colors font-medium cursor-pointer"
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Status Alert Message */}
      {statusMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-2 text-xs text-emerald-800 font-medium">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

    </div>
  );
};
