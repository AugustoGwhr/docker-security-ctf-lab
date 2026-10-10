#!/usr/bin/env python3
"""Execute no seu computador. A senha nunca é gravada nem impressa."""
import getpass
import hashlib
import secrets


def encode_password(password):
    if not 12 <= len(password) <= 256:
        raise ValueError("Escolha uma senha de 12 a 256 caracteres.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600000)
    return f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}"


if __name__ == "__main__":
    first = getpass.getpass("Crie a senha do portal (mínimo 12 caracteres): ")
    second = getpass.getpass("Repita a senha: ")
    if first != second:
        raise SystemExit("As senhas não coincidem.")
    try:
        encoded = encode_password(first)
    except ValueError as exc:
        raise SystemExit(str(exc))
    print("Cole esta linha nos Secrets do Streamlit, fora do GitHub:")
    print(f'PORTAL_PASSWORD_HASH = "{encoded}"')
