import React from 'react';
import { Wallet, TrendingUp, Bell } from 'lucide-react';

export const Home: React.FC = () => {
  return (
    <div className="page home-page">
      <header className="page-header">
        <h1>Pepe</h1>
        <button className="icon-button">
          <Bell size={24} />
        </button>
      </header>

      <section className="portfolio-section">
        <div className="portfolio-card">
          <div className="portfolio-icon">
            <Wallet size={32} />
          </div>
          <div className="portfolio-info">
            <span className="portfolio-label">Portfolio Value</span>
            <span className="portfolio-value">$0.00</span>
            <span className="portfolio-change positive">+0.00%</span>
          </div>
        </div>
      </section>

      <section className="quick-stats">
        <div className="stat-card">
          <TrendingUp size={20} />
          <span className="stat-label">BTC</span>
          <span className="stat-value">$0.00</span>
        </div>
        <div className="stat-card">
          <TrendingUp size={20} />
          <span className="stat-label">ETH</span>
          <span className="stat-value">$0.00</span>
        </div>
        <div className="stat-card">
          <TrendingUp size={20} />
          <span className="stat-label">GOLD</span>
          <span className="stat-value">$0.00</span>
        </div>
      </section>

      <section className="recent-activity">
        <h2>Recent Activity</h2>
        <div className="activity-list">
          <p className="empty-state">No recent activity</p>
        </div>
      </section>
    </div>
  );
};
