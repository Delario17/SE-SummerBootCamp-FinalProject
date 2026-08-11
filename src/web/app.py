"""FastAPI web dashboard for the Coding Agent Harness."""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path
from src.web.routes import router

app = FastAPI(title="Harness Dashboard", version="0.1.0")
app.include_router(router)

TEMPLATES_DIR = Path(__file__).parent / "templates"


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard HTML page."""
    index_path = TEMPLATES_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return HTMLResponse(
        "<html><body><h1>Harness Dashboard</h1><p>Template not found</p></body></html>"
    )