# 🐘 Elephantasm Frontend

The Next.js frontend for the Elephantasm Long-Term Agentic Memory (LTAM) framework.

## Tech Stack

- **Next.js 15.5** with App Router
- **TypeScript** for type safety
- **Tailwind CSS 4** for styling
- **React 19** for UI components

## Project Structure

```
frontend/
├── src/
│   ├── app/              # Next.js App Router pages
│   │   ├── layout.tsx    # Root layout
│   │   ├── page.tsx      # Home page
│   │   └── globals.css   # Global styles
│   ├── components/       # Reusable React components
│   ├── lib/              # Utility functions and API client
│   │   └── api.ts        # FastAPI backend client
│   └── types/            # TypeScript type definitions
│       └── index.ts      # Core Elephantasm types
├── public/               # Static assets
├── .env.local            # Environment variables (local)
├── .env.example          # Environment variables template
└── package.json          # Dependencies and scripts
```

## Getting Started

### Prerequisites

- Node.js 20+ and npm
- The Elephantasm backend running on port 8000

### Installation

1. **Fix npm cache permissions** (if needed):
   ```bash
   sudo chown -R $(id -u):$(id -g) "$HOME/.npm"
   ```

2. **Install dependencies**:
   ```bash
   npm install --legacy-peer-deps
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env.local
   ```

   Edit `.env.local` if your backend is running on a different URL.

4. **Start the development server**:
   ```bash
   npm run dev
   ```

5. **Open your browser** to [http://localhost:3000](http://localhost:3000)

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` |
| `NEXT_PUBLIC_API_V1` | API v1 prefix | `/api/v1` |
| `NEXT_PUBLIC_APP_NAME` | Application name | `Elephantasm` |

## Features

- ✅ Real-time backend health monitoring
- ✅ Type-safe API client with TypeScript
- ✅ Responsive design with Tailwind CSS
- ✅ Server-side rendering with Next.js
- 🚧 Memory visualization dashboard (coming soon)
- 🚧 Event stream monitoring (coming soon)
- 🚧 Dreamer job monitoring (coming soon)

## API Client

The frontend includes a centralized API client in `src/lib/api.ts`:

```typescript
import { apiClient, checkBackendHealth } from '@/lib/api';

// Check backend health
const health = await checkBackendHealth();

// Make custom API requests
const events = await apiClient.get('/api/v1/events');
```

## Type System

All core Elephantasm types are defined in `src/types/index.ts`:

- `Event` - Raw interactions
- `Memory` - Structured reflections
- `Lesson` - Extracted insights
- `Knowledge` - Canonicalized truths
- `Identity` - Agent dispositions
- `MemoryPack` - Compiled context bundles

## Contributing

This is part of the Elephantasm project. See the main repository README for contribution guidelines.

## License

MIT License - see LICENSE file for details.
