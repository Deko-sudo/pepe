export interface Asset {
  id: string;
  symbol: string;
  name: string;
  type: 'crypto' | 'gold';
  price: number;
  change24h: number;
  marketCap?: number;
  volume24h?: number;
}

export interface MarketData {
  assets: Asset[];
  lastUpdated: Date;
}

export interface PriceHistory {
  timestamp: Date;
  price: number;
}

export interface AnalyticsData {
  assetId: string;
  history: PriceHistory[];
  indicators: {
    rsi?: number;
    macd?: number;
    movingAverage?: number;
  };
}

export interface UserSettings {
  notifications: boolean;
  currency: 'USD' | 'EUR' | 'RUB';
  darkMode: boolean;
}
