"""
============================================================
test_main.py - Pruebas del endpoint principal (main.py)
============================================================
Descripción:
    Este módulo contiene las pruebas de integración para los
    endpoints definidos en main.py. Usa el cliente de prueba
    de FastAPI (TestClient de Starlette) para simular peticiones
    HTTP sin necesidad de levantar un servidor real.

Uso:
    Ejecutar todas las pruebas con:
        pytest tests/

    Ejecutar con detalle:
        pytest tests/ -v
============================================================
"""

# ------------------------------------------------------------
# Importaciones necesarias para las pruebas
# ------------------------------------------------------------
from fastapi.testclient import TestClient  # Cliente HTTP para pruebas sin servidor real
from main import app                        # Instancia de la aplicación FastAPI

# ------------------------------------------------------------
# Instancia del cliente de prueba
# ------------------------------------------------------------
# Se crea una sola instancia del cliente para usar en todas las pruebas del módulo
cliente = TestClient(app)


def test_endpoint_raiz():
    """
    Prueba del endpoint raíz GET /.

    Verifica que:
        1. El servidor responde con código HTTP 200 (OK).
        2. La respuesta contiene la clave 'mensaje'.
        3. El estado del servidor es 'activo'.
    """
    # Se realiza la petición GET al endpoint raíz
    respuesta = cliente.get("/")

    # Se verifica que el servidor responde correctamente
    assert respuesta.status_code == 200, "El endpoint raíz debe retornar HTTP 200"

    # Se convierte la respuesta a diccionario para verificar su contenido
    datos = respuesta.json()
    assert "mensaje" in datos, "La respuesta debe contener la clave 'mensaje'"
    assert datos["estado"] == "activo", "El estado del servidor debe ser 'activo'"


def test_endpoint_health():
    """
    Prueba del endpoint de salud GET /health.

    Verifica que:
        1. El servidor responde con código HTTP 200 (OK).
        2. El estado reportado es 'saludable'.
    """
    # Se realiza la petición GET al endpoint de salud
    respuesta = cliente.get("/health")

    # Se verifica que el código de respuesta es 200
    assert respuesta.status_code == 200, "El endpoint /health debe retornar HTTP 200"

    # Se verifica que el estado reportado es el correcto
    datos = respuesta.json()
    assert datos["estado"] == "saludable", "El estado del servidor debe ser 'saludable'"
