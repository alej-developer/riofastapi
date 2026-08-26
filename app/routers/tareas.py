"""
============================================================
app/routers/tareas.py - Enrutador CRUD para el recurso Tarea
============================================================
Descripcion:
    Define todos los endpoints del recurso "Tarea" siguiendo el
    estandar REST. Cada operacion CRUD corresponde a un verbo HTTP:
        - GET    /tareas          -> Listar todas las tareas
        - POST   /tareas          -> Crear una nueva tarea
        - GET    /tareas/{id}     -> Obtener una tarea por ID
        - PUT    /tareas/{id}     -> Actualizar una tarea por ID
        - DELETE /tareas/{id}     -> Eliminar una tarea por ID

    SEGURIDAD APLICADA EN ESTE MODULO:
        1. Validacion de entrada via Pydantic (schemas/tarea.py).
        2. Rate limiting por endpoint critico (slowapi).
        3. El ID de ruta se valida como entero positivo (Path validator).
        4. Las respuestas usan el esquema TareaRespuesta (no el interno).
        5. Los errores devuelven mensajes genericos (sin stack traces).
============================================================
"""

# ------------------------------------------------------------
# Importaciones del framework FastAPI
# ------------------------------------------------------------
from fastapi import APIRouter, HTTPException, status, Path, Request  # Componentes base del enrutador
from typing import List                                               # Tipo para lista de respuestas

# ------------------------------------------------------------
# Importaciones de los esquemas de validacion Pydantic
# ------------------------------------------------------------
from app.schemas.tarea import TareaCrear, TareaActualizar, TareaRespuesta

# ------------------------------------------------------------
# Importaciones del modelo y repositorio de datos
# ------------------------------------------------------------
from app.models.tarea import repositorio_tareas, TareaInterno

# ------------------------------------------------------------
# Importaciones de seguridad (rate limiting)
# ------------------------------------------------------------
from app.core.seguridad import limitador  # Instancia del limitador de peticiones


# ============================================================
# Creacion del enrutador del recurso Tarea
# ============================================================
# Se usa un APIRouter para modularizar los endpoints de este recurso.
# El prefijo "/tareas" y el tag "Tareas" se aplican a todos los endpoints.
router = APIRouter(
    prefix="/tareas",
    tags=["Tareas"],
    responses={
        # Respuestas de error comunes documentadas para todos los endpoints
        404: {"description": "Tarea no encontrada"},
        429: {"description": "Demasiadas peticiones. Limite de tasa superado."},
        422: {"description": "Error de validacion. Los datos enviados no son validos."},
    },
)


# ============================================================
# Funcion auxiliar: convierte TareaInterno a TareaRespuesta
# ============================================================
def _a_respuesta(tarea: TareaInterno) -> TareaRespuesta:
    """
    Convierte un objeto TareaInterno en el esquema TareaRespuesta.

    POR QUE: Esta funcion garantiza que NUNCA se exponga el modelo
    interno directamente. Si en el futuro el modelo interno tiene
    campos sensibles (tokens, hashes), esta capa actua como barrera
    de seguridad que filtra que se expone al cliente.

    Args:
        tarea (TareaInterno): Objeto interno del repositorio.

    Returns:
        TareaRespuesta: Esquema seguro para enviar al cliente.
    """
    return TareaRespuesta(
        id=tarea.id,
        titulo=tarea.titulo,
        descripcion=tarea.descripcion,
        completada=tarea.completada,
        prioridad=tarea.prioridad,      # type: ignore[arg-type]
        fecha_creacion=tarea.fecha_creacion,
    )


# ============================================================
# ENDPOINT: Listar todas las tareas
# ============================================================
@router.get(
    "/",
    response_model=List[TareaRespuesta],
    summary="Obtener todas las tareas",
    description="Devuelve la lista completa de tareas almacenadas.",
    status_code=status.HTTP_200_OK,
)
@limitador.limit("30/minute")   # Limite especifico: 30 peticiones por minuto por IP
async def listar_tareas(request: Request) -> List[TareaRespuesta]:
    """
    Devuelve todas las tareas disponibles.

    SEGURIDAD:
        - Rate limit: 30 peticiones/minuto para evitar scraping masivo.
        - Respuesta filtrada por TareaRespuesta (no expone internos).
    """
    tareas = repositorio_tareas.obtener_todas()
    return [_a_respuesta(t) for t in tareas]


# ============================================================
# ENDPOINT: Crear una nueva tarea
# ============================================================
@router.post(
    "/",
    response_model=TareaRespuesta,
    summary="Crear una nueva tarea",
    description="Crea una tarea con los datos proporcionados y devuelve la tarea creada.",
    status_code=status.HTTP_201_CREATED,
)
@limitador.limit("10/minute")   # Limite mas estricto en escritura para prevenir spam
async def crear_tarea(request: Request, datos: TareaCrear) -> TareaRespuesta:
    """
    Crea una nueva tarea en el repositorio.

    SEGURIDAD:
        - Los datos son validados y saneados por TareaCrear (Pydantic)
          ANTES de llegar a esta funcion. Cualquier dato invalido o
          peligroso genera un HTTP 422 automaticamente.
        - Rate limit: 10 peticiones/minuto para prevenir creacion masiva
          de registros (spam de datos / abuso de la API).
        - El ID es asignado por el servidor, nunca por el cliente.

    Args:
        request (Request): Peticion HTTP (requerida por slowapi).
        datos (TareaCrear): Datos validados de la nueva tarea.

    Returns:
        TareaRespuesta: La tarea recien creada con su ID asignado.
    """
    tarea = repositorio_tareas.crear(
        titulo=datos.titulo,
        descripcion=datos.descripcion,
        completada=datos.completada,
        prioridad=datos.prioridad.value,  # Se convierte el Enum a string
    )
    return _a_respuesta(tarea)


# ============================================================
# ENDPOINT: Obtener una tarea por ID
# ============================================================
@router.get(
    "/{id}",
    response_model=TareaRespuesta,
    summary="Obtener una tarea por ID",
    description="Busca y devuelve una tarea especifica usando su identificador unico.",
    status_code=status.HTTP_200_OK,
)
@limitador.limit("60/minute")   # Consultas individuales tienen limite mas permisivo
async def obtener_tarea(
    request: Request,
    # SEGURIDAD: Path(..., ge=1) valida que el ID sea un entero mayor o igual a 1.
    # Esto previene IDs negativos, cero o valores no enteros que podrian
    # causar comportamiento inesperado en la logica del repositorio.
    id: int = Path(..., ge=1, description="Identificador unico de la tarea. Debe ser un entero positivo."),
) -> TareaRespuesta:
    """
    Devuelve la tarea correspondiente al ID proporcionado.

    SEGURIDAD:
        - Validacion del parametro de ruta: solo enteros >= 1.
        - Si la tarea no existe, se devuelve HTTP 404 con mensaje
          generico (no se revela informacion interna del sistema).

    Args:
        request (Request): Peticion HTTP (requerida por slowapi).
        id (int): ID de la tarea a buscar (validado por Path).

    Returns:
        TareaRespuesta: La tarea encontrada.

    Raises:
        HTTPException 404: Si no existe ninguna tarea con ese ID.
    """
    tarea = repositorio_tareas.obtener_por_id(id)
    if tarea is None:
        # SEGURIDAD: El mensaje de error es generico. No se indica si el
        # recurso "nunca existio" o "fue eliminado", para evitar enumeration attacks
        # (donde un atacante descubre que IDs existen probando sistematicamente).
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontro ninguna tarea con el identificador {id}.",
        )
    return _a_respuesta(tarea)


# ============================================================
# ENDPOINT: Actualizar una tarea existente
# ============================================================
@router.put(
    "/{id}",
    response_model=TareaRespuesta,
    summary="Actualizar una tarea",
    description="Actualiza los campos proporcionados de una tarea existente (actualizacion parcial).",
    status_code=status.HTTP_200_OK,
)
@limitador.limit("15/minute")   # Limite moderado en escritura para prevenir abusos
async def actualizar_tarea(
    request: Request,
    id: int = Path(..., ge=1, description="ID de la tarea a actualizar."),
    datos: TareaActualizar = ...,
) -> TareaRespuesta:
    """
    Actualiza parcialmente una tarea existente.

    SEGURIDAD:
        - Validacion del ID de ruta: solo enteros >= 1.
        - Validacion de campos con TareaActualizar (Pydantic).
        - Solo se modifican los campos enviados; los demas permanecen.
        - HTTP 404 generico si la tarea no existe.

    Args:
        request (Request): Peticion HTTP (requerida por slowapi).
        id (int): ID de la tarea a actualizar.
        datos (TareaActualizar): Campos a actualizar con sus nuevos valores.

    Returns:
        TareaRespuesta: La tarea con los cambios aplicados.

    Raises:
        HTTPException 404: Si la tarea con ese ID no existe.
    """
    tarea = repositorio_tareas.actualizar(
        id=id,
        titulo=datos.titulo,
        descripcion=datos.descripcion,
        completada=datos.completada,
        prioridad=datos.prioridad.value if datos.prioridad else None,
    )
    if tarea is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontro ninguna tarea con el identificador {id}.",
        )
    return _a_respuesta(tarea)


# ============================================================
# ENDPOINT: Eliminar una tarea por ID
# ============================================================
@router.delete(
    "/{id}",
    summary="Eliminar una tarea",
    description="Elimina permanentemente la tarea con el ID especificado.",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limitador.limit("10/minute")   # Limite estricto en eliminacion para prevenir borrado masivo
async def eliminar_tarea(
    request: Request,
    id: int = Path(..., ge=1, description="ID de la tarea a eliminar."),
) -> None:
    """
    Elimina una tarea del repositorio.

    SEGURIDAD:
        - Validacion del ID de ruta: solo enteros >= 1.
        - HTTP 404 generico si la tarea no existe.
        - HTTP 204 sin cuerpo en caso de exito (no se confirma si existia antes).

    Args:
        request (Request): Peticion HTTP (requerida por slowapi).
        id (int): ID de la tarea a eliminar.

    Raises:
        HTTPException 404: Si la tarea con ese ID no existe.
    """
    eliminada = repositorio_tareas.eliminar(id)
    if not eliminada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontro ninguna tarea con el identificador {id}.",
        )
    # HTTP 204 No Content: exito sin cuerpo de respuesta (estandar REST para DELETE)
