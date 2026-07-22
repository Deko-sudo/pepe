import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export const Analytics: React.FC = () => {
  const mockData = [
    { time: '00:00', price: 0 },
    { time: '04:00', price: 0 },
    { time: '08:00', price: 0 },
    { time: '12:00', price: 0 },
    { time: '16:00', price: 0 },
    { time: '20:00', price: 0 }
  ];

  return (
    <div className="page analytics-page">
      <header className="page-header">
        <h1>Analytics</h1>
      </header>

      <div className="chart-container">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={mockData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="price" stroke="#007AFF" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="indicators">
        <div className="indicator-card">
          <span className="indicator-label">RSI</span>
          <span className="indicator-value">--</span>
        </div>
        <div className="indicator-card">
          <span className="indicator-label">MACD</span>
          <span className="indicator-value">--</span>
        </div>
        <div className="indicator-card">
          <span className="indicator-label">MA</span>
          <span className="indicator-value">--</span>
        </div>
      </div>

      <div className="analysis-section">
        <h2>Analysis</h2>
        <p className="empty-state">Select an asset to view analysis</p>
      </div>
    </div>
  );
};
