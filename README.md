# 🃏 Card Draft App

Esqueleto de una aplicación de draft de cartas usando:
- **Backend**: Python + FastAPI
- **Frontend**: HTML + JavaScript + CSS
- **API externa**: [Deck of Cards API](https://deckofcardsapi.com)

---

## Estructura del proyecto

```
card-draft-app/
├── backend/
│   ├── main.py              ← Punto de entrada del servidor
│   ├── requirements.txt     ← Dependencias Python
│   └── routes/
│       ├── __init__.py      ← Marca el directorio como paquete Python
│       ├── deck.py          ← Endpoints del mazo (crear, robar, barajar)
│       └── draft.py         ← Lógica del draft (crear sesión, pickear)
└── frontend/
    ├── index.html           ← Interfaz de usuario
    ├── styles.css           ← Estilos
    └── app.js               ← Lógica JS (llamadas a la API)
```

---

## Cómo correr el proyecto

### 1. Instalar dependencias del backend
```bash
cd backend
pip install -r requirements.txt
```

### 2. Correr el servidor
```bash
uvicorn main:app --reload
```
El servidor queda escuchando en: `http://localhost:8000`

Podés ver la documentación automática de la API en: `http://localhost:8000/docs`

### 3. Abrir el frontend
Abrir `frontend/index.html` directamente en el navegador.

---

## Endpoints disponibles

| Método | Endpoint                        | Descripción                  |
|--------|---------------------------------|------------------------------|
| GET    | `/`                             | Verificar que el servidor OK |
| POST   | `/deck/new`                     | Crear mazo nuevo             |
| GET    | `/deck/{deck_id}/draw?count=N`  | Robar N cartas               |
| POST   | `/deck/{deck_id}/shuffle`       | Barajar mazo existente       |
| POST   | `/draft/create`                 | Crear sesión de draft        |
| POST   | `/draft/pick`                   | Pickear una carta            |
| GET    | `/draft/{session_id}/state`     | Ver estado del draft         |
