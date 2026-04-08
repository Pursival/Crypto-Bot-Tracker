# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.

## Crypto Tracker Telegram Bot

A Python Telegram bot (`crypto_tracker_bot.py`) that tracks XRP and SOL prices via the Binance API.

### Commands
- `/start` — Welcome message and instructions
- `/set_xrp <price>` — Save your XRP buy price in USDT
- `/set_sol <price>` — Save your SOL buy price in USDT
- `/status` — Fetch live prices and show % gain/loss from your buy prices

### Config
- `TELEGRAM_BOT_TOKEN` — Set in Replit Secrets
- `crypto_data.json` — Persists your buy prices between restarts

### Running
Workflow: **Crypto Tracker Bot** — runs `python crypto_tracker_bot.py`

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
