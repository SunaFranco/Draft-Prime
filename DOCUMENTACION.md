# 🃏 Documentación Técnica del Proyecto Draft-Prime

Este documento sirve como **guía de arquitectura y referencia de desarrollo** para el proyecto **Draft-Prime**. Explica en detalle el funcionamiento actual del sistema, la pila tecnológica utilizada, el diseño del sistema de salas en tiempo real y los pasos para extender el proyecto con nuevos modos de juego o funcionalidades.

---

## 📌 1. Visión General del Proyecto

**Draft-Prime** es una plataforma web en tiempo real diseñada para jugar formatos de **Draft** y **Subastas** de juegos de cartas coleccionables (TCG como Yu-Gi-Oh!, Pokémon, etc.).

### Principales características actuales:
1. **Sistema de Salas / Sesiones en Tiempo Real**: Creación de salas multijugador con enlace directo, estados de "Listo" (*Ready*), soporte de reconexión sin pérdida de progreso y reasignación automática del rol de *Host*.
2. **Arquitectura de Modos Extensible (Plugin Pattern)**: Separación limpia entre la lógica del lobby/conexión y la lógica de cada modo de juego.
3. **Modo Implementado: Cube Draft Yu-Gi-Oh!**:
   - Selección de Cubes desde base de datos (Supabase) o archivos de texto locales.
   - Apertura de sobres simultáneos.
   - Pasaje de sobres en sentido horario / antihorario según la ronda (Draft estilo suizo/booster).
   - Integración con la API pública de **YGOPRODECK** para fetching dinámico de imágenes, tipos, ataque, defensa y efectos de cartas.
4. **Modo Base / Stub: Subasta Pokémon**: Estructura inicial registrada lista para desarrollar la mecánica de subastas.

---

## 🛠️ 2. Pila Tecnológica y Librerías Utilizadas

El proyecto sigue una arquitectura **decoupled** (Backend en Python y Frontend desacoplado en JavaScript vainilla con módulos ES6).

### 🐍 Backend (`requirements.txt`)

| Librería | Versión | Uso y Propósito en el Proyecto |
| :--- | :--- | :--- |
| **`fastapi`** | `>=0.115.0` | Framework web principal. Proporciona ruteo HTTP REST (`/session`, `/cubes`) y soporte nativo para **WebSockets**. |
| **`uvicorn`** | `>=0.32.0` | Servidor ASGI de alto rendimiento que ejecuta la aplicación FastAPI. |
| **`websockets`** | `>=13.0` | Driver subyacente para comunicación bidireccional continua entre clientes y servidor. |
| **`pydantic`** | `>=2.9.0` | Validación estricta de esquemas de datos en solicitudes HTTP (ej. `CreateSessionRequest`, `CreateCubeRequest`). |
| **`supabase`** | `>=2.0.0` | Cliente oficial de Supabase. Permite consultar y guardar Cubes y cartas en PostgreSQL en la nube. |
| **`python-dotenv`** | `>=1.0.0` | Carga variables de entorno desde el archivo `.env` (`SUPABASE_URL`, `SUPABASE_KEY`). |

#### Integraciones externas integradas en código:
- **`urllib.request` + `ssl` + `json`**: Utilizados en `backend/modes/cube_draft_yugioh/card_api.py` para consultar la API de **YGOPRODECK** (`https://db.ygoprodeck.com/api/v7/cardinfo.php`), con un sistema de caché en memoria (`CARD_CACHE`) para evitar peticiones duplicadas a la API de Yu-Gi-Oh.

---

### 🌐 Frontend (Sin Frameworks Pesados)

El frontend está implementado en **JavaScript Vainilla (ES6 Modules)**, HTML5 semántico y CSS3 moderno (Custom Properties / Variables).

- **`SessionClient` (`frontend/js/core/session.js`)**: Encapsula el cliente WebSocket (`new WebSocket(...)`) y peticiones REST (`fetch`).
- **`LocalStorage`**: Mantiene la sesión activa (`draft_prime_session_id`, `draft_prime_username`) para permitir reconexión automática tras refrescar la página.
- **Modulo System (`import/export`)**: Permite una estructura limpia sin necesidad de empaquetadores como Webpack o Vite en desarrollo.

---

## 🏛️ 3. Sistema de Salas y Conexiones en Tiempo Real

El sistema de salas está coordinado por `backend/services/session_manager.py` y `backend/routes/session.py`.

### 3.1. Estructura del Estado de una Sesión (`session` dict)

Cada sala se almacena en el diccionario `sessions` en memoria (`session_manager.py`):

```python
{
    "id": "a1b2c3d4e5f6",        # ID único hex de 12 caracteres
    "host": "Alice",             # Username del Host actual
    "players": [                 # Lista de jugadores en la sala
        {"username": "Alice", "ready": True, "connected": True},
        {"username": "Bob",   "ready": True, "connected": True}
    ],
    "max_players": 4,            # Máximo de jugadores (por defecto 4)
    "started": False,            # True cuando el draft ya inició
    "created_at": "2026-09-01...",
    "mode": "cube_draft_yugioh", # Clave del modo de juego seleccionado
    "mode_config": { ... },      # Configuración del modo (ej. cube, pack_count)
    "draft": { ... }             # Estado interno del juego (manejado por el Handler del modo)
}
```

### 3.2. Ciclo de Vida y Eventos WebSocket

#### 📡 Eventos Globales del Lobby (Backend -> Frontend):
- `session_state`: Sincronización completa del estado de la sala al conectar.
- `player_joined`: Notifica cuando se une o reconecta un jugador.
- `player_left`: Notifica cuando un jugador se desconecta (desmarca `connected` y `ready`).
- `player_ready`: Notifica cambio en el estado `ready` de un jugador.
- `all_ready`: Emitido cuando todos los jugadores conectados están listos.
- `host_changed`: Notifica si el host original se desconectó y se reasignó el rol a otro jugador.
- `mode_selection`: El host solicitó iniciar selección de modo (`start_game`).
- `mode_config`: El host seleccionó un modo (`choose_mode`).
- `mode_configured`: El host envió la configuración del modo (`configure_mode`).
- `error`: Mensajes de error enviados al cliente.

#### 🔄 Manejo de Reconexiones:
Si un jugador cierra la pestaña o pierde internet:
1. `WebSocketDisconnect` captura el evento en `session.py`.
2. `manager.disconnect(...)` remueve el socket.
3. El jugador permanece en `session["players"]`, pero con `connected: False`.
4. Si el jugador reconecta con el mismo `username`, `existing_player` en `session.py` lo re-asocia, marca `connected: True` y le envía `session_state` con su estado exacto de juego procesado por `get_player_sync_state()`.

---

## 🎯 4. Patrón de Modos de Juego (Game Modes Framework)

Para que agregar nuevos juegos (Pokémon, Magic, Lorcana, etc.) sea limpio y mantenible, el proyecto usa el **Plugin Pattern** en ambos lados:

### Backend: `BaseGameMode` (`backend/modes/base.py`)
Cada modo implementa la interfaz abstracta `BaseGameMode`:

```python
class BaseGameMode(ABC):
    @property
    def key(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def requires_cubes(self) -> bool: ...
    
    def get_public_config_options(self, session: dict) -> dict: ...
    def get_player_sync_state(self, session: dict, username: str) -> dict: ...
    def validate_config(self, message: dict) -> dict: ...
    def start_game(self, session: dict) -> None: ...
    async def handle_action(self, session, username, action, message, websocket, manager) -> bool: ...
```

- **Registro Dinámico (`backend/modes/registry.py`)**: Todos los modos se registran en `_REGISTERED_MODES`. `routes/session.py` delega automáticamente cualquier acción desconocida por el lobby al handler activo.

### Frontend: `BaseGameModeUI` (`frontend/modes/base_mode.js`)
Cada modo en el cliente hereda de `BaseGameModeUI`:

```javascript
export class BaseGameModeUI {
  renderConfigFields(containerEl, data, isHost) {}
  readConfigFields(containerEl) {}
  handleEvent(event, data, context) {}
  resetState() {}
}
```

- **Registro en Frontend (`frontend/app.js`)**: El diccionario `modeUIRegistry` relaciona la clave del modo (`cube_draft_yugioh`, `subasta_pokemon`, etc.) con su controlador de UI.

---

## 🚀 5. Guía Paso a Paso para Implementar Nuevas Funcionalidades

### 💡 Ejemplo A: Crear un Nuevo Modo de Juego (ej: `draft_magic`)

#### Paso 1: Crear la estructura de carpetas en el Backend
Crea `backend/modes/draft_magic/handler.py`.

```python
from backend.modes.base import BaseGameMode

class DraftMagicMode(BaseGameMode):
    @property
    def key(self) -> str:
        return "draft_magic"

    @property
    def name(self) -> str:
        return "Draft Magic: The Gathering"

    def validate_config(self, message: dict) -> dict:
        return {"set_code": message.get("set_code", "FDN")}

    def start_game(self, session: dict) -> None:
        session["magic_draft"] = {"step": 1, "cards": []}

    async def handle_action(self, session, username, action, message, websocket, manager) -> bool:
        if action == "magic_pick_card":
            # Tu lógica de pick aquí
            return True
        return False
```

#### Paso 2: Registrar el modo en Backend
Abre `backend/modes/registry.py`:
```python
from backend.modes.draft_magic.handler import DraftMagicMode

register_mode(DraftMagicMode())
```

#### Paso 3: Crear el controlador UI en Frontend
Crea `frontend/modes/draft_magic/magic_draft.js`:
```javascript
import { BaseGameModeUI } from "../base_mode.js";

export class MagicDraftModeUI extends BaseGameModeUI {
  constructor() {
    super("draft_magic", "Draft Magic");
  }

  renderConfigFields(containerEl, data, isHost) {
    containerEl.innerHTML = `
      <label>Edición de Magic:</label>
      <input type="text" id="magic-set" value="FDN" ${!isHost ? 'disabled' : ''} />
    `;
  }

  readConfigFields(containerEl) {
    return { set_code: document.getElementById("magic-set").value };
  }

  handleEvent(event, data, context) {
    if (event === "magic_card_picked") {
      // Actualizar UI
      return true;
    }
    return false;
  }
}
```

#### Paso 4: Registrar en Frontend `app.js`
En `frontend/app.js`:
```javascript
import { MagicDraftModeUI } from "./modes/draft_magic/magic_draft.js";

const modeUIRegistry = {
  cube_draft_yugioh: new YugiohDraftModeUI(),
  subasta_pokemon: new SubastaPokemonModeUI(),
  draft_magic: new MagicDraftModeUI(), // <-- Añadir aquí
};
```

---

## 📁 6. Mapa de Archivos del Proyecto

```
Draft-Prime/
├── DOCUMENTACION.md                # Este documento de arquitectura
├── backend/
│   ├── database.py                 # Conexión Supabase PostgreSQL & Helper local fallback
│   ├── main.py                     # Instancia FastAPI, CORS y declaración de rutas
│   ├── requirements.txt            # Dependencias Python
│   ├── modes/
│   │   ├── base.py                 # Clase base abstracta BaseGameMode
│   │   ├── registry.py             # Registro dinámico de modos de juego
│   │   ├── cube_draft_yugioh/      # Lógica de Yu-Gi-Oh Draft & API YGOPRODECK
│   │   └── subasta_pokemon/        # Stub para Subasta Pokémon
│   ├── routes/
│   │   ├── session.py              # Endpoints REST y WebSocket de salas (/session)
│   │   └── cubes.py                # Endpoints REST para gestión de Cubes (/cubes)
│   └── services/
│       └── session_manager.py      # ConnectionManager (WebSocket active sockets & sessions memory)
├── frontend/
│   ├── index.html                  # Estructura HTML principal (Pantallas: Home, Lobby, Mode, Draft)
│   ├── styles.css                  # Estilos UI responsive
│   ├── app.js                      # Punto de entrada JS y Event Dispatcher principal
│   ├── config.js                   # Configuración global de URLs de la API
│   ├── js/core/
│   │   ├── session.js              # Clase SessionClient para REST & WebSocket
│   │   └── ui.js                   # Helpers para cambio de pantalla y renderizado de lista de jugadores
│   └── modes/
│       ├── base_mode.js            # Interfaz BaseGameModeUI para el cliente
│       ├── cube_draft_yugioh/      # Lógica de UI para Yu-Gi-Oh Draft
│       └── subasta_pokemon/        # Lógica de UI para Subasta Pokémon
└── README.md                       # Guía rápida de inicio
```

---

## 🛠️ 7. Instrucciones para Ejecutar Localmente

### Backend
```bash
# 1. Crear entorno virtual (opcional pero recomendado)
python -m venv venv
venv\Scripts\activate  # En Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar servidor en modo reload
python -m uvicorn backend.main:app --reload --port 8000
```

### Frontend
El frontend se puede servir directamente con cualquier servidor estático (ej. Live Server en VS Code o `python -m http.server 3000` dentro de la carpeta `frontend/`).
