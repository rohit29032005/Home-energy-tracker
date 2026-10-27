import React, { useState } from 'react';
import { Plus, Trash2, Cpu, MapPin, Zap, X } from 'lucide-react';
import type { Device, User } from '../types';

interface DeviceManagementProps {
  devices: Device[];
  currentUser: User | null;
  onAddDevice: (device: Partial<Device>) => Promise<void>;
  onDeleteDevice: (deviceId: number) => Promise<void>;
}

export const DeviceManagement: React.FC<DeviceManagementProps> = ({
  devices,
  currentUser,
  onAddDevice,
  onDeleteDevice
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [type, setType] = useState('KITCHEN');
  const [location, setLocation] = useState('Kitchen');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !currentUser) return;

    setIsSubmitting(true);
    try {
      await onAddDevice({
        name: name.trim(),
        type,
        location,
        userId: currentUser.id
      });
      setName('');
      setIsModalOpen(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 tracking-tight">Registered Household Appliances</h2>
          <p className="text-xs text-slate-500">Manage connected devices and appliance-level consumption tracking</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-xs transition-colors cursor-pointer self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          Add Appliance
        </button>
      </div>

      {/* Device Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {devices.map(device => (
          <div
            key={device.id}
            className="bg-slate-50 rounded-xl p-4 border border-slate-200 hover:border-slate-300 transition-all flex flex-col justify-between group"
          >
            <div>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-emerald-600 shadow-2xs">
                    <Cpu className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 leading-tight">{device.name}</h4>
                    <span className="text-[11px] font-medium text-slate-500 bg-white px-2 py-0.5 rounded-md border border-slate-200 inline-block mt-1">
                      {device.type}
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => onDeleteDevice(device.id)}
                  title="Remove device"
                  className="text-slate-400 hover:text-red-600 p-1 rounded-lg hover:bg-red-50 transition-colors opacity-80 group-hover:opacity-100 cursor-pointer"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <div className="mt-4 space-y-1.5 text-xs text-slate-600">
                <div className="flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span>{device.location}</span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-200/80 flex items-center justify-between text-xs">
              <span className="text-slate-500 font-medium">3-Day Usage:</span>
              <span className="font-bold text-slate-900 flex items-center gap-1 bg-white px-2.5 py-1 rounded-md border border-slate-200">
                <Zap className="w-3.5 h-3.5 text-amber-500 fill-current" />
                {(device.energyConsumed || 0).toFixed(1)} kWh
              </span>
            </div>
          </div>
        ))}

        {devices.length === 0 && (
          <div className="col-span-full py-12 text-center bg-slate-50 rounded-xl border border-dashed border-slate-300">
            <Cpu className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm font-medium text-slate-600">No appliances registered yet.</p>
            <p className="text-xs text-slate-400 mt-1">Click "Add Appliance" to register your smart devices.</p>
          </div>
        )}
      </div>

      {/* Add Device Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 relative animate-in fade-in zoom-in-95 duration-200">
            
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <h3 className="text-base font-bold text-slate-900">Register New Appliance</h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Appliance Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Living Room Air Conditioner"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="w-full text-xs p-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Appliance Type</label>
                  <select
                    value={type}
                    onChange={e => setType(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
                  >
                    <option value="HVAC">HVAC / Cooling</option>
                    <option value="KITCHEN">Kitchen Appliance</option>
                    <option value="ENTERTAINMENT">Entertainment / TV</option>
                    <option value="OFFICE">Office / Workstation</option>
                    <option value="UTILITY">Utility / Laundry</option>
                    <option value="GENERAL">General Plug</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Location</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Master Bedroom"
                    value={location}
                    onChange={e => setLocation(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div className="pt-3 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-xs transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? 'Saving...' : 'Register Appliance'}
                </button>
              </div>
            </form>

          </div>
        </div>
      )}

    </div>
  );
};
