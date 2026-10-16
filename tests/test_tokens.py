"""
Tests de JWT: el algoritmo queda fijado al decodificar.

python-jose 3.3.0 aceptaba claves y algoritmos de forma laxa y permitía
falsificar tokens (GHSA-6c5p-j8vq-pqhj, GHSA-3qf3-8w2g-rqmx). PyJWT solo
verifica el algoritmo que esta función le pasa.
"""

import base64
import json
import warnings

import jwt
import pytest
from jwt.warnings import InsecureKeyLengthWarning

from app.core.config import configuracion
from app.core.tokens import crear_token, decodificar_token


def _segmento(datos: dict) -> str:
    """Codifica un segmento JWT en base64url sin relleno."""
    crudo = json.dumps(datos, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(crudo).rstrip(b"=").decode("ascii")


def test_decodificar_fija_el_algoritmo_configurado(monkeypatch: pytest.MonkeyPatch) -> None:
    """La verificación solo declara ALGORITMO_JWT, nunca una lista abierta."""
    capturado: dict = {}

    def falso_decode(token: str, clave: str, algorithms=None, **kwargs):
        capturado["token"] = token
        capturado["clave"] = clave
        capturado["algorithms"] = algorithms
        return {"sub": "ok"}

    monkeypatch.setattr("app.core.tokens.jwt.decode", falso_decode)

    assert decodificar_token("token-de-prueba") == {"sub": "ok"}
    assert capturado["algorithms"] == [configuracion.ALGORITMO_JWT]
    assert capturado["clave"] == configuracion.CLAVE_SECRETA
    assert "none" not in capturado["algorithms"]


def test_roundtrip_con_el_algoritmo_configurado() -> None:
    """Un token firmado con el algoritmo configurado se verifica."""
    datos = decodificar_token(crear_token({"sub": "usuario-prueba"}))
    assert datos["sub"] == "usuario-prueba"


def test_rechaza_token_firmado_con_otro_algoritmo() -> None:
    """Un HS384 no debe colar cuando la API solo admite el algoritmo fijado."""
    # La clave de la app es de HS256; HS384 avisa de longitud y debe rechazarse igual.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", InsecureKeyLengthWarning)
        otro = jwt.encode(
            {"sub": "atacante"},
            configuracion.CLAVE_SECRETA,
            algorithm="HS384",
        )
    with pytest.raises(jwt.InvalidTokenError):
        decodificar_token(otro)


def test_rechaza_algoritmo_none() -> None:
    """El ataque clásico alg=none no supera la verificación."""
    token = f"{_segmento({'alg': 'none', 'typ': 'JWT'})}.{_segmento({'sub': 'atacante'})}."
    with pytest.raises(jwt.InvalidTokenError):
        decodificar_token(token)


def test_rechaza_algoritmo_none_aunque_este_configurado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ni siquiera una configuración errónea puede desactivar la firma."""
    monkeypatch.setattr(configuracion, "ALGORITMO_JWT", "none")
    with pytest.raises(ValueError, match="algoritmo de firma explícito"):
        decodificar_token("no-importa")
