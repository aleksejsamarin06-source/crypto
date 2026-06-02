import base64
import gzip
import hashlib
import hmac
import json
import os
from typing import Dict, Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


PBKDF2_ITERATIONS = 100000
EXPORT_VERSION = "1.0"
SOURCE_APPLICATION = "CryptoSafe Manager"


def canonical_json(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64decode(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def derive_export_keys(password: str, salt: bytes, key_bits: int = 256) -> tuple:
    if not password:
        raise ValueError("Укажите пароль импортируемого файла")
    if key_bits not in (128, 256):
        raise ValueError("key_bits must be 128 or 256")

    key_length = key_bits // 8
    material = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        key_length + 32,
    )
    return material[:key_length], material[key_length:]


def encrypt_with_password(data: Dict[str, Any], password: str,
                          key_bits: int = 256, compress: bool = False) -> Dict[str, Any]:
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key, signing_key = derive_export_keys(password, salt, key_bits)

    plaintext = canonical_json(data)
    compression = "gzip" if compress else "none"
    if compress:
        plaintext = gzip.compress(plaintext)

    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    package = {
        "version": EXPORT_VERSION,
        "metadata": data.get("metadata", {}),
        "encryption": {
            "method": "password",
            "algorithm": f"AES-{key_bits}-GCM",
            "key_derivation": "PBKDF2-HMAC-SHA256",
            "iterations": PBKDF2_ITERATIONS,
            "salt": b64encode(salt),
            "nonce": b64encode(nonce),
            "compression": compression,
        },
        "data": b64encode(ciphertext),
        "integrity": {
            "payload_hash": sha256_hex(canonical_json(data)),
            "ciphertext_hash": sha256_hex(ciphertext),
            "signature_algorithm": "HMAC-SHA256",
        },
    }
    signature_payload = canonical_json({
        "version": package["version"],
        "metadata": package["metadata"],
        "encryption": package["encryption"],
        "data": package["data"],
        "integrity": {
            "payload_hash": package["integrity"]["payload_hash"],
            "ciphertext_hash": package["integrity"]["ciphertext_hash"],
            "signature_algorithm": package["integrity"]["signature_algorithm"],
        },
    })
    package["integrity"]["signature"] = b64encode(hmac.new(signing_key, signature_payload, hashlib.sha256).digest())
    return package


def decrypt_with_password(package: Dict[str, Any], password: str) -> Dict[str, Any]:
    encryption = package.get("encryption", {})
    algorithm = encryption.get("algorithm", "AES-256-GCM")
    key_bits = 128 if "128" in algorithm else 256
    salt = b64decode(encryption["salt"])
    nonce = b64decode(encryption["nonce"])
    ciphertext = b64decode(package["data"])
    key, signing_key = derive_export_keys(password, salt, key_bits)

    signature_payload = canonical_json({
        "version": package.get("version"),
        "metadata": package.get("metadata", {}),
        "encryption": encryption,
        "data": package.get("data"),
        "integrity": {
            "payload_hash": package.get("integrity", {}).get("payload_hash"),
            "ciphertext_hash": package.get("integrity", {}).get("ciphertext_hash"),
            "signature_algorithm": package.get("integrity", {}).get("signature_algorithm"),
        },
    })
    expected = hmac.new(signing_key, signature_payload, hashlib.sha256).digest()
    actual = b64decode(package.get("integrity", {}).get("signature", ""))
    if not hmac.compare_digest(expected, actual):
        raise ValueError("Invalid package signature")

    if sha256_hex(ciphertext) != package.get("integrity", {}).get("ciphertext_hash"):
        raise ValueError("Invalid ciphertext hash")

    plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    if encryption.get("compression") == "gzip":
        plaintext = gzip.decompress(plaintext)
    data = json.loads(plaintext.decode("utf-8"))
    if sha256_hex(canonical_json(data)) != package.get("integrity", {}).get("payload_hash"):
        raise ValueError("Invalid payload hash")
    return data


def encrypt_with_public_key(data: Dict[str, Any], public_key_pem: bytes,
                            key_bits: int = 256, compress: bool = False) -> Dict[str, Any]:
    if key_bits not in (128, 256):
        raise ValueError("key_bits must be 128 or 256")

    symmetric_key = os.urandom(key_bits // 8)
    nonce = os.urandom(12)
    plaintext = canonical_json(data)
    compression = "gzip" if compress else "none"
    if compress:
        plaintext = gzip.compress(plaintext)

    ciphertext = AESGCM(symmetric_key).encrypt(nonce, plaintext, None)
    public_key = serialization.load_pem_public_key(public_key_pem)
    encrypted_key = public_key.encrypt(
        symmetric_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    return {
        "version": EXPORT_VERSION,
        "metadata": data.get("metadata", {}),
        "encryption": {
            "method": "public_key",
            "algorithm": f"RSA-OAEP/AES-{key_bits}-GCM",
            "key_size": 2048,
            "nonce": b64encode(nonce),
            "compression": compression,
        },
        "encrypted_key": b64encode(encrypted_key),
        "data": b64encode(ciphertext),
        "integrity": {
            "payload_hash": sha256_hex(canonical_json(data)),
            "ciphertext_hash": sha256_hex(ciphertext),
            "signature_algorithm": "SHA256",
            "signature": sha256_hex(canonical_json(data) + ciphertext).encode("ascii").decode("ascii"),
        },
    }


def decrypt_with_private_key(package: Dict[str, Any], private_key_pem: bytes,
                             password: bytes = None) -> Dict[str, Any]:
    private_key = serialization.load_pem_private_key(private_key_pem, password=password)
    symmetric_key = private_key.decrypt(
        b64decode(package["encrypted_key"]),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    encryption = package.get("encryption", {})
    ciphertext = b64decode(package["data"])
    if sha256_hex(ciphertext) != package.get("integrity", {}).get("ciphertext_hash"):
        raise ValueError("Invalid ciphertext hash")

    plaintext = AESGCM(symmetric_key).decrypt(b64decode(encryption["nonce"]), ciphertext, None)
    if encryption.get("compression") == "gzip":
        plaintext = gzip.decompress(plaintext)
    data = json.loads(plaintext.decode("utf-8"))
    if sha256_hex(canonical_json(data)) != package.get("integrity", {}).get("payload_hash"):
        raise ValueError("Invalid payload hash")
    return data


def clear_bytes(data):
    if isinstance(data, bytearray):
        for index in range(len(data)):
            data[index] = 0
