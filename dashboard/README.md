# BasisPoint Dashboard

React dashboard for multi-exchange cryptocurrency funding rate visualization.

## Prerequisites

- Node.js 18+
- npm 9+
- Backend API running on port 8000 (see root README for backend setup)

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Setup Environment

```bash
npm run setup
```

This automatically creates `.env` from `.env.example`. Alternatively, copy manually:

```bash
cp .env.example .env
```

### 3. Start Development Server

```bash
npm start
```

Opens [http://localhost:3000](http://localhost:3000) in your browser.

## Available Scripts

| Script | Description |
|--------|-------------|
| `npm run setup` | Create .env from template (safe to run multiple times) |
| `npm start` | Start development server (port 3000) |
| `npm run build` | Create production build in `build/` |
| `npm test` | Run test suite |
| `npm run analyze` | Analyze bundle size |
| `npx tsc --noEmit` | TypeScript type checking |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REACT_APP_API_URL` | Yes | `http://localhost:8000` | Backend API server URL |

## Project Structure

```
src/
  components/           # React components
    ui/                 # shadcn/ui base components (Button, Card, Table, etc.)
    Grid/               # Data grid components (AssetFundingGridV2)
    Charts/             # Visualization (Recharts-based)
    Arbitrage/          # Arbitrage filtering and display
    Cards/              # Dashboard metric cards
    Layout/             # Page layout components
  lib/                  # Shared utilities
    utils.ts            # Class name merging (cn function)
    queryClient.ts      # TanStack Query configuration
  pages/                # Route page components
  services/             # API client and type definitions
  types/                # TypeScript interfaces
  hooks/                # Custom React hooks
```

## Tech Stack

- **React 19** - UI framework
- **TypeScript 4.9** - Type safety
- **TanStack Table 8** - Headless table library
- **TanStack Query 5** - Server state management with 30s auto-refresh
- **Tailwind CSS 3.4** - Utility-first styling
- **shadcn/ui** - Accessible component primitives (built on Radix UI)
- **Recharts 3** - Charting library
- **Axios** - HTTP client
- **React Router 6** - Client-side routing

## Troubleshooting

### TypeScript Errors

Run type checking to identify issues:

```bash
npx tsc --noEmit
```

### API Connection Failed

1. Ensure backend is running:
   ```bash
   python api.py
   ```

2. Verify `REACT_APP_API_URL` in `.env` matches API port

3. Check API health:
   ```bash
   curl http://localhost:8000/api/health
   ```

### Missing Modules / Import Errors

Reinstall dependencies:

```bash
rm -rf node_modules package-lock.json
npm install
```

### Development Server Hangs

If `npm start` hangs at "Starting the development server...":

1. Delete node_modules and reinstall:
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

2. Clear npm cache if problem persists:
   ```bash
   npm cache clean --force
   npm install
   ```

### Port 3000 Already in Use

Find and kill the process using port 3000:

**Windows:**
```bash
netstat -ano | findstr :3000
taskkill /PID <pid> /F
```

**Linux/Mac:**
```bash
lsof -i :3000
kill -9 <pid>
```

## Build for Production

```bash
npm run build
```

Creates optimized production build in `build/` directory. Serve with any static file server.

## Related Documentation

- [API Reference](../docs/API_REFERENCE.md) - Backend API endpoints
- [Main README](../README.md) - Full system setup
- [Troubleshooting](../docs/TROUBLESHOOTING.md) - Common issues
