# Local 3D Agent

This project is a local-first agentic 3D pipeline for Windows:

- React UI for prompt entry, file upload, event streaming, and GLB preview
- FastAPI orchestrator with a tool-using agent loop
- Ollama with `mistral:7b` for structured tool selection
- InstantMesh CLI integration for image-to-3D generation
- Blender MCP integration over stdio for model import and post-processing
- SQLite job persistence and SSE job updates

## Architecture

```text
React UI
  -> FastAPI orchestrator
  -> Ollama (Mistral)
  -> InstantMesh CLI
  -> MCP stdio client
  -> Blender MCP server
  -> Blender
```

## Repository Layout

- `backend/`: FastAPI app, agent loop, tool adapters, SQLite jobs
- `frontend/`: React + Vite UI with SSE updates and Three.js preview
- `docs/windows-setup.md`: Windows installation and configuration guide

## Current Machine State

This workspace session confirmed:

- `ollama` is installed
- `python` was not found on `PATH`
- `node` and `npm` were not found on `PATH`
- `git` was not found on `PATH`

You need those installed before the project can run locally.

## Backend Run

```powershell
.\backend_runtime\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## One-Click Launch

Use [start-agentic-blender.cmd](c:/Users/gHOST/Downloads/New%20folder/start-agentic-blender.cmd).

That starts Blender, and Blender's startup hook then:

- starts the local addon socket on `127.0.0.1:9876`
- starts the backend on `127.0.0.1:8000`
- starts the agent UI on `127.0.0.1:4173`
- opens the `Local 3D Agent` browser app window next to Blender

This is the intended day-to-day entrypoint on Windows.

## Frontend Run

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

## Notes

- The repository now includes a concrete `backend/.env` pointing at the local vendorized `blender-mcp` venv.
- The frontend assumes the backend is reachable at `http://127.0.0.1:8000`.
- Generated and uploaded files are served from `backend/data/` through `/files/...`.
