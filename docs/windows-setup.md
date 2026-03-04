# Windows Setup

This guide is written for Windows PowerShell and matches the scaffold in this repository.

## 1. Install Required Tools

Install these before running the project:

1. Python 3.11 or newer
2. Node.js 20 or newer
3. Git for Windows
4. Blender
5. Ollama

As of Tuesday, March 3, 2026, the current workspace session could only confirm `ollama` on `PATH`. Python, Node.js, npm, and Git were not available in this shell session.

## 2. Pull the Model in Ollama

```powershell
ollama pull mistral:7b
ollama run mistral:7b
```

## 3. Install Blender MCP

Configure your Blender MCP server so it can be started from a command line. The backend talks to it over MCP stdio and requires:

- `BLENDER_MCP_COMMAND`
- `BLENDER_MCP_ARGS`

Example pattern:

```env
BLENDER_MCP_COMMAND=npx
BLENDER_MCP_ARGS=-y,@some/blender-mcp-server
```

Replace that with the actual command for the MCP server you choose.

## 4. Install InstantMesh

```powershell
git clone https://github.com/TencentARC/InstantMesh.git
cd InstantMesh
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Test your local inference command separately first. The backend expects a command shape like:

```powershell
python run.py --image input.png --output output.glb
```

Then point the backend at the exact Python executable and script:

```env
INSTANTMESH_PYTHON=C:\path\to\InstantMesh\.venv\Scripts\python.exe
INSTANTMESH_SCRIPT=C:\path\to\InstantMesh\run.py
INSTANTMESH_EXTRA_ARGS=
```

## 5. Configure Backend Environment

From `backend/`, create `.env` from `.env.example`, then fill in the local paths:

```env
OLLAMA_MODEL=mistral:7b
INSTANTMESH_PYTHON=C:\path\to\InstantMesh\.venv\Scripts\python.exe
INSTANTMESH_SCRIPT=C:\path\to\InstantMesh\run.py
BLENDER_MCP_COMMAND=npx
BLENDER_MCP_ARGS=-y,blender-mcp-server
```

## 6. Start the Backend

```powershell
.\backend_runtime\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 7. Start the Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

## 8. Expected Workflow

1. Upload an image in the UI.
2. Submit a generation or modification prompt.
3. The backend creates a job and streams events over SSE.
4. InstantMesh generates a `.glb` if needed.
5. Blender MCP imports the model and applies normalization or modifications.
6. The final `.glb` is served back to the UI and displayed in the viewer.

## 9. Daily Launch

Once the repository is set up, use:

```powershell
.\start-agentic-blender.cmd
```

Blender startup now auto-boots the local agent workspace and opens the agent window beside Blender.

## Constraints

- Single-image 3D generation is approximate.
- The current tool executor includes a simple action mapper for prompts like "make it taller" and "add metallic material".
- For richer modifications, extend the agent prompt and Blender MCP tool mappings in `backend/app/services/tools.py`.
