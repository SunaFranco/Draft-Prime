import asyncio
import gc
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routes import auth, session, cubes, pve
from backend.modes.cube_draft_yugioh.card_api import CARD_CACHE
from backend.modes.subasta_pokemon.poke_api import POKE_CACHE
from backend.services.session_manager import cleanup_inactive_sessions, sessions


def get_process_memory_mb():
    """Devuelve el RSS actual en Linux, si está disponible."""
    try:
        with open("/proc/self/status", encoding="utf-8") as status_file:
            for line in status_file:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except (OSError, ValueError):
        pass
    return None


async def memory_cleanup_loop():
    """Tarea en segundo plano que limpia sesiones inactivas y fuerza garbage collection periódicamente."""
    while True:
        try:
            await asyncio.sleep(600)  # Cada 10 minutos
            cleaned = cleanup_inactive_sessions()
            gc.collect()
            rss_mb = get_process_memory_mb()
            rss_label = f"{rss_mb:.1f}" if rss_mb is not None else "unavailable"
            print(
                f"[MEMORY] rss_mb={rss_label} sessions={len(sessions)} "
                f"pokemon_cache={len(POKE_CACHE)} card_cache={len(CARD_CACHE)} "
                f"sessions_cleaned={cleaned}"
            )
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[CLEANUP ERROR] Error durante limpieza de memoria: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(memory_cleanup_loop())
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Card Draft API",
    description="Backend de draft de cartas con sistema de sesiones en tiempo real",
    version="0.2.0",
    lifespan=lifespan,
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
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(pve.router, prefix="/api/pve", tags=["PVE"])


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

