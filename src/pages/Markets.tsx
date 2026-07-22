import React from 'react';
import { Search, Filter } from 'lucide-react';

export const Markets: React.FC = () => {
  return (
    <div className="page markets-page">
      <header className="page-header">
        <h1>Markets</h1>
        <div className="header-actions">
          <button className="icon-button">
            <Search size={24} />
          </button>
          <button className="icon-button">
            <Filter size={24} />
          </button>
        </div>
      </header>

      <div className="search-bar">
        <input type="text" placeholder="Search assets..." />
      </div>

      <div className="market-tabs">
        <button className="tab active">All</button>
        <button className="tab">Crypto</button>
        <button className="tab">Gold</button>
      </div>

      <div className="market-list">
        <div className="empty-state">No assets available</div>
      </div>
    </div>
  );
};
