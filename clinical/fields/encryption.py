"""
AES-256-GCM field-level encryption for PHI at rest.

Ciphertext is stored as base64(url-safe) with a prepended 12-byte nonce.
Decryption occurs transparently on read; encryption on write/save.
"""
from __future__ import annotations

import base64
import hashlib
import os
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def _derive_aes_key(raw_key: str) -> bytes:
    """Normalize configured key material to exactly 32 bytes for AES-256."""
    try:
        decoded = base64.urlsafe_b64decode(raw_key + "==")
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass
    return hashlib.sha256(raw_key.encode("utf-8")).digest()


class AES256Cipher:
    """Singleton-style cipher wrapper used by encrypted model fields."""

    _instance: Optional["AES256Cipher"] = None

    def __init__(self) -> None:
        key_material = getattr(settings, "FIELD_ENCRYPTION_KEY", None)
        if not key_material:
            raise RuntimeError("FIELD_ENCRYPTION_KEY must be configured for PHI encryption.")
        self._aesgcm = AESGCM(_derive_aes_key(key_material))

    @classmethod
    def instance(cls) -> "AES256Cipher":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    _PREFIX = "enc:v1:"

    def encrypt(self, plaintext: str) -> str:
        if plaintext is None:
            return ""
        if plaintext.startswith(self._PREFIX):
            return plaintext
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        token = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
        return f"{self._PREFIX}{token}"

    def decrypt(self, token: str) -> str:
        if not token:
            return ""
        if not token.startswith(self._PREFIX):
            return token
        try:
            raw = base64.urlsafe_b64decode(token[len(self._PREFIX) :].encode("ascii"))
            nonce, ciphertext = raw[:12], raw[12:]
            return self._aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
        except Exception as exc:
            raise ValidationError("Unable to decrypt protected health field.") from exc


class EncryptedMixin:
    """Shared get_prep_value / from_db_value logic for encrypted Char/Text fields."""

    def get_prep_value(self, value: Any) -> Optional[str]:
        if value in (None, ""):
            return value
        return AES256Cipher.instance().encrypt(str(value))

    def from_db_value(self, value: Optional[str], expression, connection) -> Optional[str]:
        if value in (None, ""):
            return value
        return AES256Cipher.instance().decrypt(value)

    def to_python(self, value: Any) -> Optional[str]:
        if value in (None, ""):
            return value
        if isinstance(value, str) and value.startswith(AES256Cipher._PREFIX):
            return AES256Cipher.instance().decrypt(value)
        return value


class EncryptedCharField(EncryptedMixin, models.CharField):
    """CharField storing AES-256-GCM ciphertext in the database."""


class EncryptedTextField(EncryptedMixin, models.TextField):
    """TextField storing AES-256-GCM ciphertext in the database."""
