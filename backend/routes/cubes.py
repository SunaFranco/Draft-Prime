"""
routes/cubes.py - API Endpoints para la gestión de Cubes

Proporciona rutas para:
  - Listar cubes públicos y personalizados
  - Obtener el contenido detallado de un cube
  - Crear un nuevo cube con su lista de cartas
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database import get_all_cubes, get_cube_by_id, create_new_cube

router = APIRouter()


class CreateCubeRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    author: Optional[str] = "Anon"
    cards: List[str]


@router.get("/", response_model=List[dict])
def list_cubes():
    """Retorna la lista de todos los Cubes disponibles."""
    return get_all_cubes()


@router.get("/{cube_id}")
def get_cube(cube_id: str):
    """Retorna la información y cartas de un Cube específico."""
    cube = get_cube_by_id(cube_id)
    if not cube:
        raise HTTPException(status_code=404, detail="Cube no encontrado.")
    return cube


@router.post("/", status_code=210)    
def create_cube(req: CreateCubeRequest):
    """NO HACE NADA AUN"""
    """Crea un nuevo Cube con su lista de cartas."""
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="El título del Cube no puede estar vacío.")
    if not req.cards:
        raise HTTPException(status_code=400, detail="El Cube debe contener al menos una carta.")

    new_cube = create_new_cube(
        title=req.title,
        description=req.description or "",
        cards=req.cards,
        author=req.author or "Anon"
    )
    return {"status": "ok", "cube": new_cube}
