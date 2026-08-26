"""
============================================================
app/schemas/tarea.py - Esquemas de validación para el modelo Tarea
============================================================
Descripcion:
    Define los esquemas Pydantic que controlan qué datos se aceptan
    en las peticiones (Request) y qué datos se devuelven en las
    respuestas (Response) para el recurso "Tarea".

    El uso de Pydantic como capa de validación es una medida de
    seguridad activa: los datos entrantes se validan y convierten
    al tipo esperado ANTES de llegar al código de negocio.
    Esto previene ataques como inyección de tipos, desbordamientos
    y manipulación de campos no esperados.
============================================================
"""

# ------------------------------------------------------------
# Importaciones de Pydantic para definición y validación de esquemas
# ------------------------------------------------------------
from pydantic import BaseModel, Field, field_validator  # Clases base y validadores
from typing import Optional                              # Para campos opcionales
from datetime import datetime                            # Para el campo de fecha de creación
from enum import Enum                                    # Para el campo de prioridad restringido


# ============================================================
# Enumeración de prioridades permitidas
# ============================================================
# SEGURIDAD: Usar un Enum restringe el campo 'prioridad' a un conjunto
# fijo de valores. Cualquier valor fuera del Enum causará un error de
# validación antes de llegar al controlador, evitando datos maliciosos.
class Prioridad(str, Enum):
    """Niveles de prioridad válidos para una tarea."""
    baja = "baja"         # Prioridad baja
    media = "media"       # Prioridad media (valor por defecto)
    alta = "alta"         # Prioridad alta


# ============================================================
# Esquema base: campos comunes a todos los esquemas de Tarea
# ============================================================
class TareaBase(BaseModel):
    """
    Esquema base con los campos compartidos por las operaciones
    de creación y actualización.

    Aplica validaciones estrictas para prevenir datos maliciosos:
        - Longitud máxima en campos de texto (evita payloads enormes).
        - Caracteres permitidos en el título (previene inyección).
        - Tipos explícitos para cada campo.
    """

    # Campo título: texto corto descriptivo de la tarea
    # SEGURIDAD: min_length=1 evita títulos vacíos; max_length=100 limita
    # el tamaño del payload para prevenir ataques de desbordamiento de buffer.
    titulo: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Título descriptivo de la tarea. Entre 1 y 100 caracteres.",
        examples=["Revisar el informe mensual"],
    )

    # Campo descripción: texto largo opcional con detalle de la tarea
    # SEGURIDAD: max_length=500 impide descripciones masivas que consuman
    # recursos del servidor (ataque de consumo de memoria).
    descripcion: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Descripción opcional. Máximo 500 caracteres.",
        examples=["Revisar las métricas del mes de agosto y preparar resumen."],
    )

    # Campo completada: estado booleano de la tarea
    # SEGURIDAD: tipo bool explícito previene que se envíen valores no
    # booleanos (por ejemplo, strings "true" o enteros 1/0 sin conversión).
    completada: bool = Field(
        default=False,
        description="Indica si la tarea ha sido completada.",
    )

    # Campo prioridad: nivel de urgencia restringido al Enum Prioridad
    prioridad: Prioridad = Field(
        default=Prioridad.media,
        description="Nivel de prioridad: 'baja', 'media' o 'alta'.",
    )

    # --------------------------------------------------------
    # Validador personalizado para el campo 'titulo'
    # --------------------------------------------------------
    @field_validator("titulo")
    @classmethod
    def validar_titulo(cls, valor: str) -> str:
        """
        Valida que el título no contenga caracteres peligrosos.

        SEGURIDAD: Filtra caracteres HTML/JavaScript especiales (<, >, &, ", ')
        para prevenir ataques de Cross-Site Scripting (XSS) en caso de que
        el valor sea renderizado en un cliente web sin escapar.

        Args:
            valor (str): El valor del campo 'titulo' recibido en la petición.

        Returns:
            str: El título saneado y sin espacios extra.

        Raises:
            ValueError: Si el título contiene caracteres no permitidos.
        """
        # Se define el conjunto de caracteres que indican posible inyección
        caracteres_peligrosos = {"<", ">", '"', "'", ";", "--", "/*", "*/"}

        for caracter in caracteres_peligrosos:
            if caracter in valor:
                # Se lanza un error explícito con un mensaje descriptivo
                raise ValueError(
                    f"El título contiene el carácter no permitido: '{caracter}'. "
                    "Están prohibidos los caracteres HTML y SQL especiales."
                )

        # Se retorna el valor sin espacios iniciales ni finales
        return valor.strip()


# ============================================================
# Esquema para CREAR una nueva tarea (request body)
# ============================================================
class TareaCrear(TareaBase):
    """
    Esquema utilizado en el endpoint POST /tareas.
    Hereda todos los campos y validaciones de TareaBase.
    No incluye campos generados por el servidor (id, fecha_creacion).
    """
    pass


# ============================================================
# Esquema para ACTUALIZAR una tarea existente (request body)
# ============================================================
class TareaActualizar(BaseModel):
    """
    Esquema utilizado en el endpoint PUT /tareas/{id}.
    Todos los campos son opcionales para permitir actualizaciones parciales.

    SEGURIDAD: Al igual que TareaBase, aplica las mismas restricciones
    de longitud y tipo para evitar que una actualización parcial introduzca
    datos maliciosos.
    """
    titulo: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Nuevo título de la tarea.",
    )
    descripcion: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Nueva descripción de la tarea.",
    )
    completada: Optional[bool] = Field(
        default=None,
        description="Nuevo estado de completitud.",
    )
    prioridad: Optional[Prioridad] = Field(
        default=None,
        description="Nueva prioridad de la tarea.",
    )

    @field_validator("titulo")
    @classmethod
    def validar_titulo(cls, valor: Optional[str]) -> Optional[str]:
        """
        Aplica la misma validación de caracteres peligrosos al título
        en operaciones de actualización.
        """
        if valor is None:
            return valor

        caracteres_peligrosos = {"<", ">", '"', "'", ";", "--", "/*", "*/"}
        for caracter in caracteres_peligrosos:
            if caracter in valor:
                raise ValueError(
                    f"El título contiene el carácter no permitido: '{caracter}'."
                )
        return valor.strip()


# ============================================================
# Esquema de respuesta: lo que devuelve la API al cliente
# ============================================================
class TareaRespuesta(TareaBase):
    """
    Esquema utilizado en todas las respuestas de los endpoints de tareas.
    Incluye los campos generados por el servidor: id y fecha_creacion.

    SEGURIDAD: Definir un esquema de respuesta explícito evita la
    exposición accidental de campos internos o sensibles del modelo
    (por ejemplo, claves o metadatos de base de datos).
    """
    id: int = Field(description="Identificador único de la tarea generado por el servidor.")
    fecha_creacion: datetime = Field(description="Fecha y hora UTC en que se creó la tarea.")

    class Config:
        """
        Configuración interna del esquema de respuesta.
        from_attributes=True permite construir el esquema desde
        instancias de objetos ORM (como SQLAlchemy).
        """
        from_attributes = True
