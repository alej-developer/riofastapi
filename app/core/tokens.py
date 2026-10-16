"""
============================================================
app/core/tokens.py - Emisión y verificación de JWT
============================================================
Descripción:
    Sustituye a python-jose, vulnerable a falsificación por confusión
    de algoritmo (GHSA-6c5p-j8vq-pqhj y GHSA-3qf3-8w2g-rqmx).

    PyJWT exige la lista de algoritmos al decodificar. Este módulo
    solo acepta ALGORITMO_JWT: el llamador no puede ampliar la lista
    ni usar el algoritmo "none".
============================================================
"""

from typing import Any

import jwt

from app.core.config import configuracion


def _algoritmo_fijado() -> str:
    """
    Devuelve el único algoritmo de firma permitido.

    Rechaza el valor vacío y "none": con "none" el token no lleva
    firma y cualquiera puede fabricarlo.
    """
    algoritmo = configuracion.ALGORITMO_JWT.strip()
    if not algoritmo or algoritmo.lower() == "none":
        raise ValueError("ALGORITMO_JWT debe ser un algoritmo de firma explícito")
    return algoritmo


def crear_token(datos: dict[str, Any]) -> str:
    """
    Firma un JWT con la clave y el algoritmo configurados.

    Args:
        datos: Claims que irán en el payload.

    Returns:
        Token JWT compacto (header.payload.firma).
    """
    token = jwt.encode(
        datos,
        configuracion.CLAVE_SECRETA,
        algorithm=_algoritmo_fijado(),
    )
    if isinstance(token, bytes):
        return token.decode("ascii")
    return token


def decodificar_token(token: str) -> dict[str, Any]:
    """
    Verifica un JWT aceptando únicamente ALGORITMO_JWT.

    El argumento `algorithms` es una lista de un solo elemento.
    Un token firmado con otro algoritmo, o con "none", no se acepta:
    así se corta la confusión de algoritmo.

    Args:
        token: JWT compacto.

    Returns:
        Claims verificados.
    """
    return jwt.decode(
        token,
        configuracion.CLAVE_SECRETA,
        algorithms=[_algoritmo_fijado()],
    )
