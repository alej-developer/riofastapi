"""
CLAVE_SECRETA es obligatoria: sin ella la aplicacion no arranca.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Configuracion, obtener_configuracion

RAIZ = Path(__file__).resolve().parents[1]


def test_configuracion_exige_clave_secreta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin la variable y sin archivo .env, el modelo no se construye."""
    monkeypatch.delenv("CLAVE_SECRETA", raising=False)
    with pytest.raises(ValidationError):
        Configuracion(_env_file=None)


def test_clave_en_blanco_no_es_valida(monkeypatch: pytest.MonkeyPatch) -> None:
    """Una clave vacia o de solo espacios no cuenta como definida."""
    monkeypatch.setenv("CLAVE_SECRETA", "   ")
    with pytest.raises(ValidationError):
        Configuracion(_env_file=None)


def test_la_app_no_arranca_sin_clave_secreta(tmp_path: Path) -> None:
    """
    Importar la aplicación en un intérprete limpio, sin CLAVE_SECRETA
    y sin .env, debe fallar antes de servir tráfico.
    """
    entorno = os.environ.copy()
    entorno.pop("CLAVE_SECRETA", None)
    entorno["PYTHONPATH"] = str(RAIZ)

    resultado = subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=tmp_path,
        env=entorno,
        capture_output=True,
        text=True,
        check=False,
    )

    assert resultado.returncode != 0
    assert "CLAVE_SECRETA" in resultado.stderr


def test_obtener_configuracion_falla_sin_clave(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """El punto de arranque traduce la ausencia de clave en RuntimeError."""
    monkeypatch.delenv("CLAVE_SECRETA", raising=False)
    monkeypatch.chdir(tmp_path)
    obtener_configuracion.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="CLAVE_SECRETA"):
            obtener_configuracion()
    finally:
        monkeypatch.setenv("CLAVE_SECRETA", "clave-de-prueba-solo-para-tests-ok")
        obtener_configuracion.cache_clear()
        obtener_configuracion()
