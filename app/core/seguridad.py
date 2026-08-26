"""
============================================================
app/core/seguridad.py - Configuracion central de ciberseguridad
============================================================
Descripcion:
    Este modulo centraliza toda la configuracion de ciberseguridad
    de la API: cabeceras HTTP de seguridad, CORS y rate limiting.

    Cada filtro esta explicado con el tipo de ataque que previene.
    El objetivo es aplicar el principio de "defensa en profundidad":
    multiples capas de proteccion independientes que, juntas, reducen
    la superficie de ataque de la API.

Estructura:
    - CabecerasSeguridad: Middleware que inyecta cabeceras HTTP protectoras.
    - configurar_cors():   Configura el middleware CORS restrictivo.
    - configurar_rate_limiting(): Inicializa el limitador de peticiones.
============================================================
"""

# ------------------------------------------------------------
# Importaciones del framework y middleware
# ------------------------------------------------------------
from fastapi import FastAPI, Request, Response          # Tipos base de FastAPI
from fastapi.middleware.cors import CORSMiddleware      # Middleware CORS oficial de Starlette
from starlette.middleware.base import BaseHTTPMiddleware # Clase base para middlewares personalizados
from starlette.types import ASGIApp                     # Tipo del app ASGI

# ------------------------------------------------------------
# Importaciones para rate limiting
# ------------------------------------------------------------
from slowapi import Limiter, _rate_limit_exceeded_handler  # Motor de rate limiting
from slowapi.util import get_remote_address                 # Extrae la IP real del cliente
from slowapi.errors import RateLimitExceeded                # Excepcion de limite superado

# ------------------------------------------------------------
# Importaciones de la configuracion del proyecto
# ------------------------------------------------------------
from app.core.config import configuracion                   # Variables de entorno centralizadas


# ============================================================
# MIDDLEWARE 1: Cabeceras de seguridad HTTP
# ============================================================
class CabecerasSeguridad(BaseHTTPMiddleware):
    """
    Middleware personalizado que añade cabeceras HTTP de seguridad
    a TODAS las respuestas de la API, sin excepcion.

    POR QUE: Las cabeceras de seguridad son la primera linea de defensa
    del lado del servidor. Instruyen al navegador del cliente sobre como
    manejar el contenido de forma segura, independientemente de la logica
    de la aplicacion.

    Se implementa como middleware de Starlette para que se aplique de forma
    transversal (cross-cutting concern) sin duplicar codigo en cada endpoint.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Intercepta cada peticion, la procesa y añade las cabeceras
        de seguridad a la respuesta antes de enviarla al cliente.

        Args:
            request (Request): La peticion HTTP entrante.
            call_next: La siguiente funcion en la cadena de middlewares.

        Returns:
            Response: La respuesta HTTP con las cabeceras de seguridad añadidas.
        """
        # Se procesa la peticion y se obtiene la respuesta de la aplicacion
        respuesta = await call_next(request)

        # ------------------------------------------------------------
        # Cabecera 1: X-Content-Type-Options
        # ATAQUE PREVENIDO: MIME-Type Sniffing
        # Sin esta cabecera, algunos navegadores intentan adivinar el
        # tipo de contenido aunque el servidor lo declare explicitamente.
        # Un atacante podria subir un archivo .txt con codigo JavaScript
        # y conseguir que el navegador lo ejecute. Con "nosniff", el
        # navegador respeta siempre el Content-Type declarado.
        # ------------------------------------------------------------
        respuesta.headers["X-Content-Type-Options"] = "nosniff"

        # ------------------------------------------------------------
        # Cabecera 2: X-Frame-Options
        # ATAQUE PREVENIDO: Clickjacking
        # Un atacante puede incrustar nuestra API en un iframe invisible
        # sobre su pagina maliciosa y engañar al usuario para que haga
        # clic en botones de nuestra API sin saberlo (clickjacking).
        # "DENY" impide que cualquier pagina, incluida la nuestra,
        # pueda incrustar la aplicacion en un iframe.
        # ------------------------------------------------------------
        respuesta.headers["X-Frame-Options"] = "DENY"

        # ------------------------------------------------------------
        # Cabecera 3: X-XSS-Protection
        # ATAQUE PREVENIDO: Cross-Site Scripting (XSS) reflejado
        # Activa el filtro XSS integrado en navegadores antiguos
        # (principalmente Internet Explorer y versiones antiguas de Chrome).
        # "mode=block" detiene la carga de la pagina si detecta un ataque
        # XSS, en lugar de intentar sanear el contenido.
        # Nota: en navegadores modernos es reemplazado por Content-Security-Policy,
        # pero se mantiene por compatibilidad con clientes legacy.
        # ------------------------------------------------------------
        respuesta.headers["X-XSS-Protection"] = "1; mode=block"

        # ------------------------------------------------------------
        # Cabecera 4: Strict-Transport-Security (HSTS)
        # ATAQUE PREVENIDO: Man-in-the-Middle (MitM) y SSL Stripping
        # Fuerza al navegador a comunicarse SIEMPRE via HTTPS durante
        # el periodo de tiempo especificado (max-age=31536000 = 1 año).
        # "includeSubDomains" extiende la proteccion a todos los subdominios.
        # Un atacante que intercepte el trafico HTTP no podra degradar
        # la conexion a HTTP plano.
        # IMPORTANTE: Solo activar en produccion con HTTPS configurado.
        # ------------------------------------------------------------
        if configuracion.ENTORNO == "produccion":
            respuesta.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # ------------------------------------------------------------
        # Cabecera 5: Content-Security-Policy (CSP)
        # ATAQUE PREVENIDO: Cross-Site Scripting (XSS) y Data Injection
        # Es la defensa mas robusta contra XSS. Define las fuentes de
        # contenido que el navegador considera validas y confiables.
        # - default-src 'none': bloquea todo el contenido por defecto.
        # - script-src 'self': solo permite scripts del mismo origen.
        # - style-src 'self': solo permite estilos del mismo origen.
        # - frame-ancestors 'none': equivale a X-Frame-Options: DENY,
        #   pero con mayor soporte en navegadores modernos.
        # Para la documentacion de FastAPI (/docs) se permite 'unsafe-inline'
        # en desarrollo porque Swagger UI lo requiere.
        # ------------------------------------------------------------
        if configuracion.ENTORNO == "produccion":
            csp = (
                "default-src 'none'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
        else:
            # En desarrollo se relaja CSP para permitir la UI de Swagger/ReDoc
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "frame-ancestors 'none';"
            )
        respuesta.headers["Content-Security-Policy"] = csp

        # ------------------------------------------------------------
        # Cabecera 6: Referrer-Policy
        # ATAQUE PREVENIDO: Fuga de informacion en cabeceras Referer
        # Controla la informacion enviada en la cabecera HTTP "Referer"
        # cuando el usuario navega desde nuestra pagina a otra.
        # "strict-origin-when-cross-origin" envia solo el origen (sin
        # ruta ni parametros) en peticiones cross-origin, evitando que
        # URLs internas o tokens en la URL sean expuestos a terceros.
        # ------------------------------------------------------------
        respuesta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ------------------------------------------------------------
        # Cabecera 7: Permissions-Policy
        # ATAQUE PREVENIDO: Abuso de APIs del navegador
        # Deshabilita explicitamente el acceso a APIs del navegador que
        # la API REST no necesita (camara, microfono, geolocalizacion).
        # Esto reduce el daño en caso de un XSS exitoso, ya que el codigo
        # malicioso no podria acceder a esos recursos aunque lo intentara.
        # ------------------------------------------------------------
        respuesta.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # ------------------------------------------------------------
        # Eliminacion de cabeceras que revelan informacion del servidor
        # ATAQUE PREVENIDO: Information Disclosure / Fingerprinting
        # La cabecera "Server" informa al atacante sobre el servidor web
        # utilizado (ej: "uvicorn"). Con esa informacion puede buscar
        # vulnerabilidades especificas de esa version. Se elimina
        # para dificultar el reconocimiento (fingerprinting) del sistema.
        # ------------------------------------------------------------
        respuesta.headers.pop("server", None)  # Elimina la cabecera "server" si existe

        return respuesta


# ============================================================
# MIDDLEWARE 2: CORS (Cross-Origin Resource Sharing)
# ============================================================
def configurar_cors(app: FastAPI) -> None:
    """
    Configura el middleware CORS de forma restrictiva.

    POR QUE: CORS es un mecanismo del navegador que controla qué origenes
    (dominios) externos pueden realizar peticiones a la API.
    Sin CORS, cualquier pagina web maliciosa podria hacer peticiones a
    la API en nombre del usuario autenticado (ataque CSRF via JavaScript).

    Una politica CORS mal configurada (allow_origins=["*"]) es una
    vulnerabilidad grave porque permite que cualquier dominio acceda
    a la API con las credenciales del usuario.

    Configuracion restrictiva:
        - Solo se permiten los origenes declarados en la configuracion.
        - Solo se permiten los metodos HTTP necesarios para un CRUD REST.
        - Solo se permiten las cabeceras estrictamente necesarias.
        - allow_credentials=True permite enviar cookies de sesion,
          pero SOLO desde los origenes autorizados.

    Args:
        app (FastAPI): La instancia de la aplicacion FastAPI.
    """
    # Origenes permitidos: en produccion se deben definir los dominios reales.
    # En desarrollo se acepta localhost para facilitar las pruebas locales.
    origenes_permitidos = [
        "http://localhost:3000",        # Frontend React/Next.js en desarrollo local
        "http://localhost:5173",        # Frontend Vite en desarrollo local
        "http://127.0.0.1:8000",        # Pruebas directas contra el servidor local
    ]

    # En produccion se pueden añadir los dominios de produccion desde config
    if configuracion.ENTORNO == "produccion" and hasattr(configuracion, "ORIGENES_CORS"):
        origenes_permitidos = configuracion.ORIGENES_CORS

    app.add_middleware(
        CORSMiddleware,
        # Lista blanca de origenes autorizados.
        # JAMAS usar allow_origins=["*"] en produccion con allow_credentials=True,
        # ya que anularia la proteccion CSRF.
        allow_origins=origenes_permitidos,

        # Permite el envio de cookies y cabeceras de autorizacion.
        # REQUIERE que allow_origins NO sea ["*"].
        allow_credentials=True,

        # Metodos HTTP permitidos: solo los necesarios para un CRUD estandar.
        # Se excluye TRACE (puede usarse para ataques XST) y CONNECT.
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],

        # Cabeceras permitidas en las peticiones del cliente.
        # Se limita a lo estrictamente necesario para minimizar la superficie.
        allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
    )


# ============================================================
# RATE LIMITER: Control de tasa de peticiones
# ============================================================
# POR QUE: Un atacante puede saturar el servidor con miles de peticiones
# por segundo (ataque DDoS o brute-force). El rate limiting limita el
# numero de peticiones que un cliente puede realizar en un periodo de tiempo.
#
# Se usa la IP del cliente como clave identificadora (get_remote_address).
# En un entorno con proxy inverso (Nginx, Cloudflare) se debe configurar
# correctamente el header X-Forwarded-For para obtener la IP real.
#
# La instancia 'limitador' se exporta y se usa en los endpoints
# mediante el decorador @limitador.limit("N/periodo").
# ============================================================
limitador = Limiter(
    key_func=get_remote_address,   # Identifica al cliente por su IP remota
    default_limits=["200/day",     # Limite global: 200 peticiones por dia por IP
                    "50/hour"],    # Limite global: 50 peticiones por hora por IP
)


def configurar_rate_limiting(app: FastAPI) -> None:
    """
    Registra el limitador de peticiones en la aplicacion FastAPI.

    Añade el estado del limitador a la app y registra el manejador
    de errores que devuelve HTTP 429 (Too Many Requests) cuando
    un cliente supera el limite establecido.

    Args:
        app (FastAPI): La instancia de la aplicacion FastAPI.
    """
    # Se almacena el limitador en el estado de la app para acceso global
    app.state.limiter = limitador

    # Se registra el manejador de excepcion para el error HTTP 429.
    # Cuando un cliente supera el limite, recibe una respuesta clara
    # en lugar de un error interno del servidor.
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
