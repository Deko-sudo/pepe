import dotenv from 'dotenv';

dotenv.config();

export const config = {
  port: parseInt(process.env.PORT || '3001', 10),
  nodeEnv: process.env.NODE_ENV || 'development',
  telegramBotToken: process.env.TELEGRAM_BOT_TOKEN || '',
  telegramMiniAppName: process.env.TELEGRAM_MINI_APP_NAME || 'pepe',
  
  // API Keys for market data
  coingeckoApiKey: process.env.COINGECKO_API_KEY || '',
  goldApiUrl: process.env.GOLD_API_URL || '',
  goldApiKey: process.env.GOLD_API_KEY || '',
  
  // Rate limiting
  rateLimitWindowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '900000', 10),
  rateLimitMaxRequests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '100', 10)
};
