# Guidelines for 3D-MLOps Copilot Project

## Build & Test Commands

- **Backend:** `cd backend && uv run uvicorn app.main:app --reload`
- **Backend Tests:** `cd backend && pytest`
- **Frontend Dev:** `cd frontend && pnpm dev`
- **Frontend Build:** `cd frontend && pnpm build`

## Code Style & Architecture

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy async with SQLite. Follow PEP8.
- **Frontend:** React 18, Vite, TypeScript, Tailwind CSS, React Three Fiber (R3F), Zustand.
- **State Management:** Use Zustand stores (`useRunStore`, `useCameraStore`, `useChatStore`) as the single source of truth for cross-panel state synchronization.
- **Strict Rule:** Never expose LLM API Keys on the frontend bundle; all AI calls must proxy through FastAPI backend (`/api/copilot/chat`).
