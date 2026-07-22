# Pepe

Telegram Mini App for crypto and gold market analytics.

## Features

- Real-time cryptocurrency prices (BTC, ETH, etc.)
- Gold price tracking
- Technical indicators (RSI, MACD, Moving Averages)
- Portfolio tracking
- Price alerts and notifications
- Dark mode support

## Tech Stack

### Frontend
- React 18 with TypeScript
- Vite for build tooling
- Telegram Mini Apps SDK
- Recharts for data visualization
- Zustand for state management
- Tailwind CSS for styling

### Backend
- Node.js with Express
- TypeScript
- REST API
- Rate limiting
- Security best practices

### DevOps
- Docker & Docker Compose
- GitHub Actions CI/CD
- Nginx for frontend serving
- Multi-stage builds

## Getting Started

### Prerequisites

- Node.js 20+
- npm or yarn
- Docker (optional)
- Telegram Bot Token

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Deko-sudo/pepe.git
cd pepe
```

2. Install frontend dependencies:
```bash
npm install
```

3. Install backend dependencies:
```bash
cd server
npm install
cd ..
```

4. Copy environment variables:
```bash
cp .env.example .env
```

5. Fill in your environment variables in `.env`

### Development

Start frontend development server:
```bash
npm run dev
```

Start backend development server:
```bash
cd server
npm run dev
```

### Building

Build frontend:
```bash
npm run build
```

Build backend:
```bash
cd server
npm run build
```

### Docker

Build and run with Docker Compose:
```bash
docker compose up --build
```

The app will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:3001

## Project Structure

```
pepe/
├── src/                    # Frontend source code
│   ├── components/         # Reusable UI components
│   ├── pages/              # Page components
│   ├── hooks/              # Custom React hooks
│   ├── services/           # API services
│   ├── store/              # State management
│   ├── styles/             # CSS styles
│   ├── types/              # TypeScript types
│   └── utils/              # Utility functions
├── server/                 # Backend API
│   ├── src/
│   │   ├── config/         # Configuration
│   │   ├── controllers/    # Request handlers
│   │   ├── middleware/      # Express middleware
│   │   └── routes/         # API routes
│   └── package.json
├── .github/workflows/      # CI/CD pipeline
├── docker-compose.yml      # Docker configuration
└── README.md
```

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/market/prices` - Get current prices
- `GET /api/market/history/:assetId` - Get price history
- `GET /api/market/analytics/:assetId` - Get analytics data

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Telegram Mini Apps SDK](https://core.telegram.org/bots/webapps)
- [Recharts](https://recharts.org/)
- [Zustand](https://zustand-demo.pmnd.rs/)
