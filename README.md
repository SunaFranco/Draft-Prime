# 🎴 PRIME DRAFT

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.13-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![WebSockets](https://img.shields.io/badge/WebSockets-Real--Time-blue.svg?style=flat&logo=socketdotio&logoColor=white)](https://websockets.readthedocs.io/)
[![Supabase](https://img.shields.io/badge/Supabase-Database%20%26%20Auth-3ECF8E.svg?style=flat&logo=supabase&logoColor=white)](https://supabase.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**PRIME DRAFT** es una plataforma web multijugador en tiempo real diseñada para formatos competitivos de draft de cartas coleccionables, subastas estratégicas y campañas interactivas con un motor de combate PvE integrado.

Originalmente concebida como un prototipo de draft, la plataforma evolucionó hacia un sistema completo de salas privadas sincronizadas por WebSockets, gestión de usuarios, persistencia en la nube mediante Supabase y modos de juego temáticos profundos.

---

## 🌟 Modos de Juego

### 1. 🔥 Subasta Pokémon (Pokémon Auction Campaign & Draft)
Una campaña completa de gestión, draft y batallas dividida en **3 Años cronológicos** y **13 etapas progresivas**:
- **Subastas en Tiempo Real:** Bids dinámicos mediante WebSockets con cronómetro, presupuestos y control de sala.
- **Eventos de Turno:** Decisiones estratégicas aleatorias entre rondas con recompensas, riesgos y eventos de mercado.
- **Fase de Farmeo & Exploración:** Zonas interactivas con encuentros salvajes, búsqueda en basureros (*scavenge*), compra/venta de objetos y Máquinas Técnicas (MTs).
- **Mecánicas Avanzadas:** Evoluciones automáticas según el año de campaña (Nivel 40 y Nivel 100) y soporte para especies Fusión.
- **Exportación Showdown:** Generación instantánea del equipo en formato estándar compatible con [Pokémon Showdown](https://pokemonshowdown.com).
- **⚔️ Arena de Combate PvE:** 
  - Batallas 6v6 directas en el navegador contra entrenadores legendarios de la franquicia (Líder Brock, Campeona Cynthia, Entrenador Red, etc.).
  - Motor de combate propio en Python (`pkmn_ai_engine`) que simula el daño oficial de la franquicia, efectividad de tipos, estados alterados, Megaevoluciones, IA con lógica de predicción de cambios (*switch logic*) y registro de combate en español.
  - Interfaz gráfica responsiva (`pve_battle.html`) optimizada para móviles y escritorio.

### 2. 🃏 Yu-Gi-Oh! Cube Draft
Experiencia clásica y dinámica de draft por sobres de cartas Yu-Gi-Oh!:
- **Mecánica Pick & Pass:** Rotación sincronizada de sobres entre los jugadores de la sala en tiempo real.
- **Cubes Personalizados & Oficiales:** Soporte para formatos retro/temáticos (como el *Cube GX Raw*) y pools de cartas almacenados en base de datos.
- **Integración con YGOPRODeck API:** Previsualización en alta definición de las cartas, estadísticas, tipos y descripciones completas en un modal interactivo.

---

## 🚀 Características Principales

- **Multijugador en Vivo:** Comunicación bidireccional por WebSockets con control de latencia, desconexiones y auto-reconexión.
- **Salas Privadas y Dashboard:** Creación de salas, control de anfitrión (Host), invitación a jugadores por nombre de usuario y selector de estado "Listo".
- **Sistema de Cuentas y Roles:** Soporte para cuentas de Administrador y Jugador con avatares personalizados, cambio de contraseñas y gestión de permisos.
- **Salón de Trofeos e Historial:** Registro histórico de partidas disputadas, podios de ganadores y personalización de trofeos con sprites de Pokémon.
- **Arquitectura Modular Extensible:** Sistema de registro dinámico (`BaseGameMode`) que permite crear y conectar nuevos modos de juego o TCGs (como Magic: The Gathering o Disney Lorcana) sin alterar el núcleo de sesiones.
- **Frontend Ligero sin Build Step:** Construido con Vanilla JavaScript modular (ES6 Modules), HTML5 semántico y CSS3 moderno (diseño dark glassmorphism). No requiere `npm`, `webpack` ni `vite` para compilar, ofreciendo tiempos de carga instantáneos.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnologías |
|---|---|
| **Backend** | Python 3.11+, FastAPI, Uvicorn, WebSockets, Pydantic v2 |
| **Base de Datos & Auth** | Supabase (PostgreSQL), Row Level Security, JSONB Storage |
| **Frontend** | Vanilla JavaScript (ES Modules), HTML5, CSS3 Glassmorphism |
| **Motor de IA & Combate** | Custom Python Engine (`pkmn_ai_engine`), Pokédex & Movepool JSON |
| **APIs Externas** | PokéAPI, YGOPRODeck API |
| **Testing** | Pytest, Asyncio Test Suite |

---

## 📁 Estructura del Repositorio

```text
Draft-Prime/
├── backend/
│   ├── main.py                     # Punto de entrada de FastAPI y servidor de estáticos
│   ├── database.py                 # Conexión y operaciones con Supabase / PostgreSQL
│   ├── requirements.txt            # Dependencias del backend
│   ├── engine/
│   │   └── pkmn_ai_engine/         # Motor de simulación e IA de combate Pokémon
│   │       ├── ai/                 # Agente IA, evaluador de amenazas y lógica de cambio
│   │       ├── core/               # Modelos, daño, megaevoluciones y base de movimientos
│   │       ├── resolver/           # Motor de resolución de combate por turnos
│   │       └── presets.py          # Entrenadores rivales prefabricados (Brock, Cynthia, Red)
│   ├── modes/                      # Modos de juego registrados
│   │   ├── base.py                 # Clase abstracta BaseGameMode
│   │   ├── registry.py             # Registro dinámico de modos
│   │   ├── cube_draft_yugioh/      # Lógica del draft de Yu-Gi-Oh!
│   │   └── subasta_pokemon/        # Lógica de la subasta, eventos, farmeo y campaña
│   ├── routes/                     # Endpoints REST y WebSocket
│   │   ├── auth.py                 # Autenticación, perfiles y administración
│   │   ├── cubes.py                # Gestión de cubes de cartas
│   │   ├── pve.py                  # API REST del simulador de batallas PvE
│   │   └── session.py              # WebSocket de salas y sincronización en tiempo real
│   └── services/
│       └── session_manager.py      # Gestor de conexiones activas y estado de salas
├── frontend/
│   ├── index.html                  # Pantalla principal (Lobby, Salas, Modos y Draft)
│   ├── pve_battle.html             # Pantalla dedicada a la arena de combate PvE
│   ├── styles.css                  # Estilos globales y responsive
│   ├── config.js                   # Configuración de URLs de API y WebSocket
│   ├── app.js                      # Orquestador del frontend
│   ├── js/
│   │   ├── core/                   # Módulos centrales (auth, sesión, UI)
│   │   ├── pve_battle_ui.js        # Lógica de la arena de combate PvE
│   │   └── showdown_text_es.js     # Textos de batalla en español
│   └── modes/                      # Controladores frontend de cada modo
│       ├── cube_draft_yugioh/      # UI del draft de Yu-Gi-Oh!
│       └── subasta_pokemon/        # UI de la subasta, farmeo y team builder
├── supabase/
│   ├── migrations/                 # Migraciones SQL de base de datos
│   └── manual/                     # Scripts SQL manuales e inserción de datos iniciales
├── tests/                          # Suite de tests unitarios y de integración
├── Procfile                        # Comando de arranque para despliegue en PaaS
└── requirements.txt                # Dependencias raíz
```

---

## ⚙️ Instalación y Puesta en Marcha

### 1. Clonar el Repositorio
```bash
git clone https://github.com/tu-usuario/Draft-Prime.git
cd Draft-Prime
```

### 2. Configurar el Entorno Virtual
```bash
# Crear entorno virtual con Python 3.11 o superior
python -m venv .venv

# Activar entorno virtual
# En Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# En Linux/macOS:
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno
Copiá el archivo de ejemplo y completá tus credenciales de Supabase:
```bash
cp .env.example .env
```

Editá `.env`:
```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-anon-o-service-role-key
```

> **Nota:** Las tablas y esquemas necesarios se encuentran en el directorio [`supabase/migrations/`](supabase/migrations/). Ejecútalos en el SQL Editor de tu proyecto en Supabase para inicializar la base de datos.

### 4. Ejecutar el Servidor
Iniciá el backend con recarga automática:
```bash
uvicorn backend.main:app --reload --port 8000
```

- **Aplicación Web:** `http://localhost:8000`
- **Documentación Swagger:** `http://localhost:8000/docs`
- **Documentación Redoc:** `http://localhost:8000/redoc`

*FastAPI sirve automáticamente la carpeta `frontend/` en la raíz `/` de forma estática.*

---

## 🌐 Configuración del Frontend

En [`frontend/config.js`](frontend/config.js) podés definir los endpoints según el entorno:

```javascript
// Para desarrollo local:
window.API_URL = "http://localhost:8000";
window.WS_URL = "ws://localhost:8000";

// Para producción (por ejemplo en Render/Railway):
// window.API_URL = "https://tu-dominio.onrender.com";
// window.WS_URL = "wss://tu-dominio.onrender.com";
```

Si no se especifican variables, el cliente detecta automáticamente si estás en `localhost` y se conecta a los puertos predeterminados.

---

## 🧪 Pruebas (Testing)

El proyecto cuenta con pruebas automáticas para el motor de IA, cálculo de daño y rutas PvE:

```bash
pytest tests/ -v
```

---

## 🚢 Despliegue en Producción

El repositorio incluye un archivo [`Procfile`](Procfile) listo para plataformas como **Render**, **Railway** o **Heroku**:

```text
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1
```

Asegúrate de configurar en el panel del servicio las variables de entorno `SUPABASE_URL` y `SUPABASE_KEY`.

---

## ⚖️ Descargo de Responsabilidad (Disclaimer)

Este es un proyecto no comercial desarrollado por la comunidad con fines educativos y de entretenimiento. 
- **Pokémon** y sus contenidos son marcas registradas de Nintendo, Creatures Inc. y Game Freak Inc.
- **Yu-Gi-Oh!** y sus contenidos son marcas registradas de Studio Dice, Shueisha, TV Tokyo y Konami.
- Todos los datos e imágenes se obtienen de APIs públicas de la comunidad ([PokéAPI](https://pokeapi.co) y [YGOPRODeck](https://ygoprodeck.com)).
