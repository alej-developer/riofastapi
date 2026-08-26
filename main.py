"""
============================================================
main.py - Punto de entrada principal de la API REST
============================================================
Descripcion:
    Este archivo inicializa la aplicacion FastAPI y registra, en orden
    correcto, todos los middlewares de ciberseguridad y los enrutadores
    de recursos.

    ORDEN DE REGISTRO DE MIDDLEWARES:
    El orden importa: los middlewares se aplican de afuera hacia adentro
    en la cadena de peticion, y de adentro hacia afuera en la respuesta.
    El orden correcto para maxima seguridad es:

        1. Rate Limiting       <- Se aplica primero para rechazar trafico
                                  excesivo antes de procesar nada.
        2. CORS                <- Valida el origen de la peticion.
        3. Cabeceras de Seguridad <- Añade protecciones a la respuesta.

Uso:
    Modo desarrollo (con recarga automatica):
        uvicorn main:app --reload

    Modo produccion:
        uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
============================================================
"""

# ------------------------------------------------------------
# Importaciones del framework FastAPI
# ------------------------------------------------------------
from fastapi import FastAPI                    # Clase principal de la aplicacion
from fastapi.responses import JSONResponse     # Para respuestas JSON personalizadas
from fastapi.staticfiles import StaticFiles    # Para servir archivos estaticos (HTML, CSS, JS)
from pathlib import Path                       # Para construir rutas de directorios de forma segura

# ------------------------------------------------------------
# Importaciones de la libreria estandar de Python
# ------------------------------------------------------------
from datetime import datetime, timezone        # Para timestamps en UTC

# ------------------------------------------------------------
# Importaciones de los modulos de ciberseguridad del proyecto
# ------------------------------------------------------------
from app.core.seguridad import (
    CabecerasSeguridad,          # Middleware de cabeceras HTTP de seguridad
    configurar_cors,             # Funcion para registrar el middleware CORS
    configurar_rate_limiting,    # Funcion para registrar el rate limiter
)

# ------------------------------------------------------------
# Importaciones de los enrutadores de recursos
# ------------------------------------------------------------
from app.routers import tareas  # Enrutador CRUD para el recurso Tarea


# ============================================================
# Creacion de la instancia principal de la aplicacion FastAPI
# ============================================================
app = FastAPI(
    title="Rio API",
    description=(
        "API REST construida con FastAPI y Python. "
        "Incluye CRUD de tareas con validacion estricta de datos (Pydantic), "
        "CORS restrictivo, rate limiting por IP y cabeceras de seguridad HTTP."
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Equipo de Desarrollo",
        "url": "https://github.com/alej-developer/riofastapi",
    },
)


# ============================================================
# REGISTRO DE MIDDLEWARES DE CIBERSEGURIDAD
# ============================================================
# IMPORTANTE: El orden de registro define el orden de ejecucion.
# Los middlewares añadidos ULTIMO se ejecutan PRIMERO en la peticion
# entrante (estructura LIFO - Last In, First Out).
# El orden definido aqui sigue las mejores practicas de seguridad.

# Paso 1: Configurar el rate limiting
# Se registra primero porque debe ser el PRIMER filtro que procese
# la peticion: rechaza trafico excesivo antes de hacer cualquier
# otro trabajo, minimizando el consumo de recursos bajo ataque.
configurar_rate_limiting(app)

# Paso 2: Configurar CORS
# Se aplica despues del rate limiting. Valida que el origen de la
# peticion sea uno de los dominios autorizados en la lista blanca.
configurar_cors(app)

# Paso 3: Añadir el middleware de cabeceras de seguridad HTTP
# Se aplica a todas las respuestas salientes. Al registrarse despues
# de CORS, se ejecuta "mas adentro" en la cadena y por tanto tiene
# la ultima oportunidad de modificar la respuesta antes de enviarla.
app.add_middleware(CabecerasSeguridad)


# ============================================================
# MONTAJE DE ARCHIVOS ESTATICOS (FRONTEND)
# ============================================================
# Se monta el directorio 'frontend/' en la ruta '/frontend'.
# Esto permite servir el HTML, CSS y JavaScript del frontend
# desde el mismo servidor FastAPI, eliminando por completo
# los problemas de CORS: el navegador ve todo en el mismo origen.
#
# Acceso: http://localhost:8000/frontend/index.html
# ============================================================
_directorio_frontend = Path(__file__).parent / "frontend"
app.mount(
    "/frontend",
    StaticFiles(directory=_directorio_frontend),
    name="frontend",
)
# ============================================================
# REGISTRO DE ENRUTADORES DE RECURSOS
# ============================================================
# Se incluye el enrutador de tareas con el prefijo /api/v1
# para versionado de la API (buena practica de diseno REST).
app.include_router(
    tareas.router,
    prefix="/api/v1",  # Prefijo de version: /api/v1/tareas
)


# ============================================================
# ENDPOINT: Verificacion de estado del servidor (Hola Mundo)
# ============================================================
@app.get(
    "/",
    summary="Verificacion de conexion",
    description=(
        "Endpoint de bienvenida. Verifica que el servidor este activo "
        "y muestra informacion basica de la API."
    ),
    tags=["Estado del Servidor"],
)
async def hola_mundo() -> dict:
    """
    Endpoint raiz de verificacion de conexion.

    Devuelve un mensaje de bienvenida, la version de la API y
    la fecha/hora actual del servidor en formato ISO 8601 UTC.

    Returns:
        dict: Informacion basica del estado del servidor.
    """
    return {
        "mensaje": "Bienvenido a la Rio API. El servidor esta activo.",
        "version": app.version,
        "estado": "activo",
        # datetime.now(timezone.utc) es la forma correcta de obtener UTC en Python moderno.
        # datetime.utcnow() esta en desuso (deprecated) desde Python 3.12.
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "documentacion": {
            "swagger": "/docs",
            "redoc": "/redoc",
        },
        "recursos": {
            "tareas": "/api/v1/tareas",
        },
    }


# ============================================================
# ENDPOINT: Comprobacion de salud del servidor (Health Check)
# ============================================================
@app.get(
    "/health",
    summary="Estado de salud de la API",
    description=(
        "Endpoint estandar de health check para orquestadores como "
        "Docker, Kubernetes o balanceadores de carga."
    ),
    tags=["Estado del Servidor"],
)
async def health_check() -> JSONResponse:
    """
    Endpoint de comprobacion de salud.

    Es una practica estandar en APIs de produccion. Permite que
    servicios externos (Docker, Kubernetes, load balancers) verifiquen
    si la aplicacion esta operativa y lista para recibir trafico.

    Returns:
        JSONResponse: HTTP 200 con estado "saludable".
    """
    return JSONResponse(
        status_code=200,
        content={
            "estado": "saludable",
            "version": app.version,
            "detalle": "El servidor esta operativo y listo para recibir solicitudes.",
        },
    )
