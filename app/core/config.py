"""
============================================================
config.py - Configuración centralizada de la aplicación
============================================================
Descripción:
    Este módulo define la clase de configuración usando Pydantic Settings,
    que carga automáticamente los valores desde variables de entorno
    o desde un archivo .env en el directorio raíz del proyecto.

    El uso de Pydantic Settings garantiza validación de tipos y
    proporciona valores por defecto seguros para desarrollo local.

Uso:
    from app.core.config import configuracion
    print(configuracion.NOMBRE_APP)
============================================================
"""

# ------------------------------------------------------------
# Importaciones necesarias para la configuración
# ------------------------------------------------------------
from pydantic_settings import BaseSettings, SettingsConfigDict  # Clase base para configuracion con variables de entorno
from functools import lru_cache              # Decorador para cachear la instancia de configuración


class Configuracion(BaseSettings):
    """
    Clase de configuración de la aplicación.

    Hereda de BaseSettings de Pydantic, lo que permite que los atributos
    se lean automáticamente desde variables de entorno o un archivo .env.
    Los valores definidos aquí son los valores por defecto para desarrollo.
    """

    # ----------------------------------------------------------
    # Información general de la aplicación
    # ----------------------------------------------------------
    NOMBRE_APP: str = "Río API"          # Nombre de la aplicación
    VERSION: str = "0.1.0"              # Versión semántica del proyecto
    DESCRIPCION: str = "API REST construida con FastAPI"  # Descripción breve

    # ----------------------------------------------------------
    # Configuración del servidor
    # ----------------------------------------------------------
    HOST: str = "0.0.0.0"              # Dirección de escucha del servidor (0.0.0.0 = todas las interfaces)
    PUERTO: int = 8000                  # Puerto en el que escucha el servidor

    # ----------------------------------------------------------
    # Configuración del entorno
    # ----------------------------------------------------------
    ENTORNO: str = "desarrollo"         # Entorno actual: "desarrollo", "pruebas" o "produccion"
    DEBUG: bool = True                  # Activar o desactivar el modo depuración

    # ----------------------------------------------------------
    # Configuración de seguridad (JWT)
    # ----------------------------------------------------------
    CLAVE_SECRETA: str = "cambia-esta-clave-en-produccion-es-muy-importante"  # Clave para firmar tokens JWT
    ALGORITMO_JWT: str = "HS256"        # Algoritmo de firma para tokens JWT
    MINUTOS_EXPIRACION_TOKEN: int = 30  # Tiempo de vida del token de acceso en minutos

    # Configuracion de Pydantic Settings V2: se usa SettingsConfigDict en lugar
    # de la clase Config interna (deprecada en Pydantic V2 / pydantic-settings).
    model_config = SettingsConfigDict(
        env_file=".env",           # Ruta al archivo de variables de entorno
        env_file_encoding="utf-8", # Codificacion del archivo .env
    )


@lru_cache()
def obtener_configuracion() -> Configuracion:
    """
    Función para obtener la instancia de configuración.

    Utiliza el decorador @lru_cache para asegurar que solo se crea
    una instancia de Configuracion durante todo el ciclo de vida
    de la aplicación (patrón Singleton).

    Returns:
        Configuracion: Instancia única de la configuración de la aplicación.
    """
    return Configuracion()


# ------------------------------------------------------------
# Instancia global de configuración
# ------------------------------------------------------------
# Se puede importar directamente en otros módulos para acceder a la configuración
configuracion = obtener_configuracion()
