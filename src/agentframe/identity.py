# src/agentframe/identity.py
from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _unb64(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def agent_id_from_pubkey(pub_raw: bytes) -> str:
    """agent_id = 'ag:' + base32(sha256(pubkey))[:16], lowercase, unpadded."""
    digest = hashlib.sha256(pub_raw).digest()
    b32 = base64.b32encode(digest).decode("ascii").lower().rstrip("=")
    return "ag:" + b32[:16]


@dataclass
class Identity:
    _priv: Ed25519PrivateKey

    @classmethod
    def generate(cls) -> "Identity":
        return cls(Ed25519PrivateKey.generate())

    @property
    def pub_raw(self) -> bytes:
        return self._priv.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )

    @property
    def pub_b64(self) -> str:
        return _b64(self.pub_raw)

    @property
    def agent_id(self) -> str:
        return agent_id_from_pubkey(self.pub_raw)

    def sign(self, msg: bytes) -> str:
        return _b64(self._priv.sign(msg))

    def save(self, path: str) -> None:
        """Write the private key PEM with owner-only permissions.

        The key is never returned or logged. Encryption-at-rest is a Phase-1
        hardening item (see DESIGN.md NEVER wall); Phase 0 relies on file perms.

        POSIX mode bits (0600) mean nothing to NTFS — os.open(..., 0o600)'s
        mode argument is silently ignored on Windows, so the file inherits
        whatever DACL its parent directory happens to grant. On win32 we
        additionally rewrite the file's DACL directly so "owner-only" is a
        real guarantee there too, not just a POSIX one.
        """
        import os
        import sys

        pem = self._priv.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(pem)
        if sys.platform == "win32":
            _restrict_to_owner_windows(path)

    @classmethod
    def load(cls, path: str) -> "Identity":
        with open(path, "rb") as f:
            priv = serialization.load_pem_private_key(f.read(), password=None)
        return cls(priv)


def _restrict_to_owner_windows(path: str) -> None:
    """Replace the file's DACL with a single ACE: current user, full control.

    PROTECTED_DACL_SECURITY_INFORMATION stops the new DACL from merging with
    whatever the parent directory would otherwise contribute (e.g. an
    inherited BUILTIN\\Users grant), so the key ends up readable by no one
    else. Windows-only; pywin32 is a conditional dependency (see
    pyproject.toml) and is never imported on other platforms.
    """
    import ntsecuritycon as con
    import win32api
    import win32security

    user_sid, _, _ = win32security.LookupAccountName("", win32api.GetUserName())

    dacl = win32security.ACL()
    dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_ALL_ACCESS, user_sid)

    sd = win32security.SECURITY_DESCRIPTOR()
    sd.SetSecurityDescriptorDacl(1, dacl, 0)

    win32security.SetFileSecurity(
        path,
        win32security.DACL_SECURITY_INFORMATION
        | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
        sd,
    )


def verify(pub_b64: str, msg: bytes, sig_b64: str) -> bool:
    try:
        pub = Ed25519PublicKey.from_public_bytes(_unb64(pub_b64))
        pub.verify(_unb64(sig_b64), msg)
        return True
    except Exception:
        return False
