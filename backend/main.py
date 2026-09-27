import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routes import session, cubes

app = FastAPI(
    title="Card Draft API",
    description="Backend de draft de cartas con sistema de sesiones en tiempo real",
    version="0.2.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Necesario para que el frontend (otro puerto/dominio) pueda hablar con la API.
# En producción, reemplazar "*" por el dominio real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rutas API ─────────────────────────────────────────────────────────────────
app.include_router(session.router, prefix="/session", tags=["Session"])
app.include_router(cubes.router, prefix="/cubes", tags=["Cubes"])


@app.get("/health")
def health():
    return {"status": "ok", "message": "Card Draft API v0.2 🃏"}


# ── Frontend estático ──────────────────────────────────────────────────────────
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {"status": "ok", "message": "Card Draft API v0.2 🃏"}

