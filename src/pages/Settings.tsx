import React from 'react';
import { Moon, Bell, Globe, Info } from 'lucide-react';

export const Settings: React.FC = () => {
  return (
    <div className="page settings-page">
      <header className="page-header">
        <h1>Settings</h1>
      </header>

      <div className="settings-list">
        <div className="setting-item">
          <div className="setting-info">
            <Moon size={20} />
            <span>Dark Mode</span>
          </div>
          <label className="toggle">
            <input type="checkbox" />
            <span className="toggle-slider"></span>
          </label>
        </div>

        <div className="setting-item">
          <div className="setting-info">
            <Bell size={20} />
            <span>Notifications</span>
          </div>
          <label className="toggle">
            <input type="checkbox" defaultChecked />
            <span className="toggle-slider"></span>
          </label>
        </div>

        <div className="setting-item">
          <div className="setting-info">
            <Globe size={20} />
            <span>Currency</span>
          </div>
          <select defaultValue="USD">
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
            <option value="RUB">RUB</option>
          </select>
        </div>

        <div className="setting-item">
          <div className="setting-info">
            <Info size={20} />
            <span>About</span>
          </div>
          <span className="setting-value">v0.1.0</span>
        </div>
      </div>
    </div>
  );
};
