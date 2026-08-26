"""
============================================================
main.py - Punto de entrada principal de la API REST
============================================================
Descripción:
    Este archivo inicializa la aplicación FastAPI, configura
    los metadatos del proyecto (título, versión, descripción)
    y registra todos los endpoints de la API.

    Actualmente expone un endpoint de verificación ("Hola Mundo")
    para comprobar que el servidor está funcionando correctamente.

Uso:
    Ejecutar en modo desarrollo con:
        uvicorn main:app --reload

    Ejecutar en modo producción con:
        uvicorn main:app --host 0.0.0.0 --port 8000
============================================================
"""

# ------------------------------------------------------------
# Importaciones del framework FastAPI
# ------------------------------------------------------------
from fastapi import FastAPI          # Clase principal para crear la aplicación
from fastapi.responses import JSONResponse  # Respuesta JSON personalizable

# ------------------------------------------------------------
# Importaciones de la librería estándar de Python
# ------------------------------------------------------------
from datetime import datetime        # Para registrar la fecha y hora del servidor

# ============================================================
# Creación de la instancia principal de la aplicación FastAPI
# ============================================================
# Se configuran los metadatos que aparecerán en la documentación
# automática generada por FastAPI (disponible en /docs y /redoc)
app = FastAPI(
    title="Río API",                               # Nombre de la API en la documentación
    description="API REST construida con FastAPI y Python. "
                "Proyecto base con configuración inicial.",  # Descripción visible en /docs
    version="0.1.0",                               # Versión semántica del proyecto
    docs_url="/docs",                              # Ruta para la documentación Swagger UI
    redoc_url="/redoc",                            # Ruta para la documentación ReDoc
    contact={
        "name": "Equipo de Desarrollo",           # Nombre del responsable del proyecto
        "url": "https://github.com/alej-developer/riofastapi",  # Repositorio del proyecto
    },
)


# ============================================================
# Endpoint raíz: Verificación de estado del servidor
# ============================================================
@app.get(
    "/",
    summary="Verificación de conexión",          # Título del endpoint en la documentación
    description="Endpoint de bienvenida. Verifica que el servidor "
                "esté activo y respondiendo correctamente.",
    tags=["Estado del Servidor"],                 # Categoría en la documentación Swagger
)
async def hola_mundo() -> dict:
    """
    Endpoint de bienvenida (Hola Mundo).

    Retorna un mensaje de bienvenida junto con la versión de la API
    y la fecha/hora actual del servidor. Útil para comprobar que
    la conexión con el servidor funciona correctamente.

    Returns:
        dict: Un diccionario con:
            - mensaje (str): Saludo de bienvenida.
            - version (str): Versión actual de la API.
            - estado (str): Estado del servidor.
            - timestamp (str): Fecha y hora actual del servidor en formato ISO 8601.
    """
    # Se construye la respuesta con información básica del servidor
    return {
        "mensaje": "¡Hola Mundo! Bienvenido a la API REST con FastAPI 🚀",
        "version": app.version,           # Versión definida al crear la instancia de FastAPI
        "estado": "activo",               # Indicador de que el servidor está funcionando
        "timestamp": datetime.utcnow().isoformat() + "Z",  # Fecha y hora UTC en formato ISO 8601
    }


# ============================================================
# Endpoint de salud: Comprobación rápida para sistemas externos
# ============================================================
@app.get(
    "/health",
    summary="Estado de salud de la API",
    description="Endpoint estándar para comprobaciones de salud (health check). "
                "Usado habitualmente por orquestadores como Docker o Kubernetes.",
    tags=["Estado del Servidor"],
)
async def health_check() -> JSONResponse:
    """
    Endpoint de comprobación de salud (Health Check).

    Este endpoint es una práctica estándar en APIs de producción.
    Permite que servicios externos (balanceadores de carga, Docker,
    Kubernetes) verifiquen si la aplicación está operativa.

    Returns:
        JSONResponse: Respuesta HTTP 200 con estado "saludable".
    """
    # Se retorna una respuesta con código HTTP 200 (OK) indicando que el servicio está sano
    return JSONResponse(
        status_code=200,
        content={
            "estado": "saludable",        # Estado del servicio
            "detalle": "El servidor está operativo y listo para recibir solicitudes.",
        },
    )
