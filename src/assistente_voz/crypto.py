"""Proteção das chaves de API em disco usando a DPAPI do Windows.

A DPAPI amarra o segredo à conta do usuário do Windows: mesmo copiando o
config.json, outra pessoa (ou outra máquina) não consegue ler a chave.

Fora do Windows, ou se algo falhar, o texto passa direto — a chave nunca é
perdida por causa da criptografia.
"""

from __future__ import annotations

import base64
import logging
import sys

PREFIX = "dpapi:v1:"
log = logging.getLogger(__name__)


def _crypt():
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):  # noqa: N801
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    return ctypes, DATA_BLOB


def is_protected(value: str) -> bool:
    return bool(value) and value.startswith(PREFIX)


def protect(text: str) -> str:
    """Criptografa para gravar em disco. Devolve o texto puro se não der."""
    if not text or is_protected(text) or sys.platform != "win32":
        return text
    try:
        ctypes, DATA_BLOB = _crypt()
        raw = text.encode("utf-8")
        buf = ctypes.create_string_buffer(raw, len(raw))
        blob_in = DATA_BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        blob_out = DATA_BLOB()
        ok = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(blob_in), "FalaAI", None, None, None, 0,
            ctypes.byref(blob_out),
        )
        if not ok:
            return text
        try:
            data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return PREFIX + base64.b64encode(data).decode("ascii")
    except Exception:  # noqa: BLE001
        log.warning("Não consegui proteger a chave; gravando sem criptografia")
        return text


def unprotect(value: str) -> str:
    """Descriptografa o que veio do disco. Texto sem marca passa direto."""
    if not is_protected(value):
        return value  # config antigo, gravado antes da criptografia
    if sys.platform != "win32":
        return ""  # protegido em outra máquina: não há como ler aqui
    try:
        ctypes, DATA_BLOB = _crypt()
        raw = base64.b64decode(value[len(PREFIX):])
        buf = ctypes.create_string_buffer(raw, len(raw))
        blob_in = DATA_BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        blob_out = DATA_BLOB()
        ok = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, None, None, None, 0,
            ctypes.byref(blob_out),
        )
        if not ok:
            log.warning("Chave protegida por outro usuário/máquina: ignorando")
            return ""
        try:
            data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return data.decode("utf-8")
    except Exception:  # noqa: BLE001
        log.warning("Não consegui ler a chave protegida")
        return ""
