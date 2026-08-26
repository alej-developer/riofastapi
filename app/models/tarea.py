"""
============================================================
app/models/tarea.py - Modelo de datos en memoria para Tarea
============================================================
Descripcion:
    Define la estructura interna del modelo Tarea y el repositorio
    en memoria que actúa como capa de persistencia temporal.

    En una aplicación real este repositorio sería reemplazado por
    una base de datos (PostgreSQL, SQLite, etc.) con un ORM como
    SQLAlchemy o Tortoise ORM. La interfaz del repositorio se mantiene
    igual para facilitar esa migración futura.

    SEGURIDAD: Al separar el modelo interno (TareaInterno) del
    esquema de respuesta (TareaRespuesta), se controla con precisión
    qué campos son visibles al exterior. Nunca se expone el modelo
    interno directamente al cliente.
============================================================
"""

# ------------------------------------------------------------
# Importaciones necesarias
# ------------------------------------------------------------
from datetime import datetime, timezone   # Para registrar la fecha de creación en UTC
from typing import Optional, Dict         # Tipos para el repositorio en memoria


# ============================================================
# Modelo interno de Tarea (usado solo dentro del servidor)
# ============================================================
class TareaInterno:
    """
    Representación interna de una tarea.

    Este modelo NO se expone directamente al cliente. Actúa como
    la entidad de dominio que el repositorio almacena y manipula.
    La separación entre modelo interno y esquema de respuesta es
    una práctica de seguridad para evitar la exposición involuntaria
    de datos sensibles.

    Attributes:
        id (int): Identificador único autoincremental.
        titulo (str): Título de la tarea (ya validado y saneado por Pydantic).
        descripcion (Optional[str]): Descripción opcional de la tarea.
        completada (bool): Estado de completitud.
        prioridad (str): Nivel de prioridad ("baja", "media" o "alta").
        fecha_creacion (datetime): Fecha y hora UTC de creación.
    """

    def __init__(
        self,
        id: int,
        titulo: str,
        descripcion: Optional[str],
        completada: bool,
        prioridad: str,
    ) -> None:
        self.id = id
        self.titulo = titulo
        self.descripcion = descripcion
        self.completada = completada
        self.prioridad = prioridad
        # Se almacena siempre en UTC para consistencia entre zonas horarias
        self.fecha_creacion = datetime.now(timezone.utc)


# ============================================================
# Repositorio en memoria: almacena y gestiona las tareas
# ============================================================
class RepositorioTareas:
    """
    Repositorio de acceso a datos para Tarea (implementación en memoria).

    Actúa como la única capa de acceso a datos para este recurso.
    Centralizar el acceso a datos en un repositorio facilita:
        - Pruebas unitarias (se puede reemplazar por un mock).
        - Migración a base de datos real sin cambiar los routers.
        - Control claro de la lógica de negocio de acceso a datos.
    """

    def __init__(self) -> None:
        # Diccionario que mapea id -> TareaInterno
        # Se usa Dict en lugar de List para O(1) en búsqueda por id
        self._tareas: Dict[int, TareaInterno] = {}

        # Contador autoincremental para generación de IDs únicos
        # SEGURIDAD: El cliente NUNCA puede asignar su propio ID.
        # Esto previene que un atacante sobreescriba registros existentes
        # enviando un ID arbitrario en el body de creación.
        self._contador_id: int = 0

    def _siguiente_id(self) -> int:
        """Genera y devuelve el siguiente ID único autoincremental."""
        self._contador_id += 1
        return self._contador_id

    # ----------------------------------------------------------
    # Operaciones CRUD
    # ----------------------------------------------------------

    def crear(
        self,
        titulo: str,
        descripcion: Optional[str],
        completada: bool,
        prioridad: str,
    ) -> TareaInterno:
        """
        Crea una nueva tarea y la almacena en el repositorio.

        Args:
            titulo: Título de la tarea (ya validado por Pydantic).
            descripcion: Descripción opcional.
            completada: Estado de completitud inicial.
            prioridad: Nivel de prioridad.

        Returns:
            TareaInterno: La tarea recién creada con su ID asignado.
        """
        nuevo_id = self._siguiente_id()
        tarea = TareaInterno(
            id=nuevo_id,
            titulo=titulo,
            descripcion=descripcion,
            completada=completada,
            prioridad=prioridad,
        )
        self._tareas[nuevo_id] = tarea
        return tarea

    def obtener_por_id(self, id: int) -> Optional[TareaInterno]:
        """
        Busca y devuelve una tarea por su ID.

        Args:
            id: Identificador único de la tarea.

        Returns:
            TareaInterno si existe, None si no se encuentra.
        """
        return self._tareas.get(id)

    def obtener_todas(self) -> list[TareaInterno]:
        """
        Devuelve todas las tareas almacenadas.

        Returns:
            Lista de todas las TareaInterno en el repositorio.
        """
        return list(self._tareas.values())

    def actualizar(
        self,
        id: int,
        titulo: Optional[str] = None,
        descripcion: Optional[str] = None,
        completada: Optional[bool] = None,
        prioridad: Optional[str] = None,
    ) -> Optional[TareaInterno]:
        """
        Actualiza los campos proporcionados de una tarea existente.
        Solo se modifican los campos que se envían (actualización parcial).

        Args:
            id: Identificador de la tarea a actualizar.
            titulo: Nuevo título (opcional).
            descripcion: Nueva descripción (opcional).
            completada: Nuevo estado (opcional).
            prioridad: Nueva prioridad (opcional).

        Returns:
            TareaInterno actualizada, o None si no existe.
        """
        tarea = self._tareas.get(id)
        if tarea is None:
            return None

        # Solo se actualiza el campo si el cliente envió un valor distinto de None
        if titulo is not None:
            tarea.titulo = titulo
        if descripcion is not None:
            tarea.descripcion = descripcion
        if completada is not None:
            tarea.completada = completada
        if prioridad is not None:
            tarea.prioridad = prioridad

        return tarea

    def eliminar(self, id: int) -> bool:
        """
        Elimina una tarea del repositorio por su ID.

        Args:
            id: Identificador de la tarea a eliminar.

        Returns:
            True si se eliminó correctamente, False si no existía.
        """
        if id not in self._tareas:
            return False
        del self._tareas[id]
        return True


# ============================================================
# Instancia global del repositorio (patrón Singleton)
# ============================================================
# Se crea una única instancia compartida por toda la aplicación.
# En una implementación real con base de datos se usaría una sesión
# por petición (dependency injection) en lugar de una instancia global.
repositorio_tareas = RepositorioTareas()
