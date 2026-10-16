"""
============================================================
config.py - Configuración centralizada de la aplicación
============================================================
Descripción:
    Este módulo define la clase de configuración usando Pydantic Settings,
    que carga automáticamente los valores desde variables de entorno
    o desde un archivo .env en el directorio raíz del proyecto.

    El uso de Pydantic Settings garantiza validación de tipos y
    proporciona valores por defecto para desarrollo local.
    CLAVE_SECRETA no tiene valor por defecto: si no está definida,
    la aplicación no arranca.

Uso:
    from app.core.config import configuracion
    print(configuracion.NOMBRE_APP)
============================================================
"""

# ------------------------------------------------------------
# Importaciones necesarias para la configuración
# ------------------------------------------------------------
from functools import lru_cache              # Decorador para cachear la instancia de configuración

from pydantic import Field, ValidationError, field_validator  # Validación de la clave secreta
from pydantic_settings import BaseSettings, SettingsConfigDict  # Clase base para configuracion con variables de entorno


class Configuracion(BaseSettings):
    """
    Clase de configuración de la aplicación.

    Hereda de BaseSettings de Pydantic, lo que permite que los atributos
    se lean automáticamente desde variables de entorno o un archivo .env.
    Los valores definidos aquí son los valores por defecto para desarrollo,
    salvo CLAVE_SECRETA, que es obligatoria.
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
    # Sin valor por defecto. Si falta en el entorno y en .env, Pydantic
    # lanza ValidationError y obtener_configuracion() impide el arranque.
    CLAVE_SECRETA: str = Field(min_length=1)  # Clave para firmar tokens JWT
    ALGORITMO_JWT: str = "HS256"        # Algoritmo de firma para tokens JWT
    MINUTOS_EXPIRACION_TOKEN: int = 30  # Tiempo de vida del token de acceso en minutos

    @field_validator("CLAVE_SECRETA")
    @classmethod
    def validar_clave_secreta(cls, valor: str) -> str:
        """
        Rechaza una clave vacía o solo con espacios.

        Una variable definida pero en blanco equivale a no tener secreto:
        la aplicación no debe arrancar en ese caso.
        """
        if not valor.strip():
            raise ValueError("CLAVE_SECRETA debe estar definida")
        return valor

    # Configuracion de Pydantic Settings V2: se usa SettingsConfigDict en lugar
    # de la clase Config interna (deprecada en Pydantic V2 / pydantic-settings).
    # extra="ignore": el README y .env.example documentan PORT, que lee el
    # contenedor (Cloud Run / Dockerfile). Esta clase usa PUERTO. Sin ignorar
    # claves desconocidas, copiar .env.example a .env impide arrancar.
    model_config = SettingsConfigDict(
        env_file=".env",           # Ruta al archivo de variables de entorno
        env_file_encoding="utf-8", # Codificacion del archivo .env
        extra="ignore",
    )


@lru_cache()
def obtener_configuracion() -> Configuracion:
    """
    Función para obtener la instancia de configuración.

    Utiliza el decorador @lru_cache para asegurar que solo se crea
    una instancia de Configuracion durante todo el ciclo de vida
    de la aplicación (patrón Singleton).

    Si CLAVE_SECRETA no está definida, lanza RuntimeError y la
    aplicación no llega a arrancar.

    Returns:
        Configuracion: Instancia única de la configuración de la aplicación.

    Raises:
        RuntimeError: CLAVE_SECRETA ausente o vacía.
    """
    try:
        return Configuracion()
    except ValidationError as error:
        campos = {err["loc"][-1] for err in error.errors() if err.get("loc")}
        if "CLAVE_SECRETA" in campos:
            raise RuntimeError(
                "CLAVE_SECRETA no está definida. "
                "Define la variable de entorno antes de arrancar la aplicación."
            ) from error
        raise


# ------------------------------------------------------------
# Instancia global de configuración
# ------------------------------------------------------------
# Se puede importar directamente en otros módulos para acceder a la configuración
configuracion = obtener_configuracion()
