"""
============================================================
tests/conftest.py - Configuracion global de fixtures para pytest
============================================================
Descripcion:
    Este modulo define los fixtures de pytest que se comparten
    entre todos los archivos de test del proyecto.

    Un fixture es una funcion que prepara el estado necesario
    para ejecutar un test y lo destruye al terminar (setup/teardown).
    Al centralizarlos en conftest.py, pytest los descubre automaticamente
    sin necesidad de importarlos en cada archivo de test.

    FIXTURES DEFINIDOS:
        - cliente: Cliente HTTP sincronico para pruebas de endpoints REST.
        - cliente_con_tareas: Cliente con datos de prueba precargados.
============================================================
"""

# ------------------------------------------------------------
# Importaciones de pytest y FastAPI
# ------------------------------------------------------------
import pytest                                  # Framework de pruebas
from fastapi.testclient import TestClient      # Cliente HTTP de prueba (no levanta servidor real)

# ------------------------------------------------------------
# Importaciones del proyecto
# ------------------------------------------------------------
from main import app                             # Instancia principal de la aplicacion
from app.models.tarea import repositorio_tareas  # Repositorio en memoria para limpiarlo entre tests
from app.core.seguridad import limitador         # Limiter de slowapi para resetear contadores


# ============================================================
# FIXTURE: cliente HTTP limpio (sin datos previos)
# ============================================================
@pytest.fixture
def cliente() -> TestClient:
    """
    Proporciona un TestClient fresco con el repositorio vacio.

    POR QUE: Cada test debe comenzar con un estado limpio y predecible.
    Si un test crea datos y el siguiente los encuentra, los resultados
    pueden variar segun el orden de ejecucion (tests acoplados).
    Limpiar el repositorio antes de cada test garantiza el aislamiento
    y la reproducibilidad: dos ejecuciones del mismo test producen
    el mismo resultado.

    Yields:
        TestClient: Cliente HTTP listo para realizar peticiones a la API.
    """
    # Se limpia el repositorio y se reinicia el contador de IDs
    # antes de cada test para garantizar aislamiento total
    repositorio_tareas._tareas.clear()
    repositorio_tareas._contador_id = 0

    # Se resetean los contadores del rate limiter entre tests.
    # slowapi almacena los contadores en memoria; sin este reset,
    # las peticiones de un test anterior pueden agotar el limite
    # de otro test que no pretende probar rate limiting, causando
    # falsos 429 y tests fragiles dependientes del orden de ejecucion.
    limitador.reset()  # Metodo publico de la API de slowapi

    # 'with' activa el ciclo de vida completo de la app (startup/shutdown events)
    with TestClient(app) as c:
        yield c

    # Limpieza posterior: se vuelve a vaciar por si el test añadio datos
    repositorio_tareas._tareas.clear()
    repositorio_tareas._contador_id = 0


# ============================================================
# FIXTURE: cliente con datos de prueba precargados
# ============================================================
@pytest.fixture
def cliente_con_tareas(cliente: TestClient) -> TestClient:
    """
    Extiende el fixture 'cliente' creando tres tareas de prueba.

    Se usa en tests que necesitan datos existentes (GET, PUT, DELETE).
    Al heredar del fixture 'cliente', el repositorio ya esta limpio.

    Args:
        cliente (TestClient): Fixture base con repositorio vacio.

    Yields:
        TestClient: Cliente con tres tareas precargadas.
    """
    # Se crean tres tareas con distintas prioridades para cubrir casos variados
    tareas_iniciales = [
        {"titulo": "Tarea de prueba uno",   "descripcion": "Primera tarea",   "prioridad": "alta"},
        {"titulo": "Tarea de prueba dos",   "descripcion": "Segunda tarea",   "prioridad": "media"},
        {"titulo": "Tarea de prueba tres",  "descripcion": "Tercera tarea",   "prioridad": "baja"},
    ]
    for datos in tareas_iniciales:
        cliente.post("/api/v1/tareas/", json=datos)

    return cliente
