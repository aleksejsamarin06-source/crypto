import base64
import hashlib
import json
import math
import time
import uuid
import zlib
from datetime import datetime, timezone
from typing import List, Dict, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec


class KeyExchangeService:
    def __init__(self, db_connection=None):
        self.db = db_connection

    def generate_rsa_key_pair(self) -> Dict[str, str]:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        return self._serialize_key_pair(private_key)

    def generate_ec_key_pair(self) -> Dict[str, str]:
        private_key = ec.generate_private_key(ec.SECP256R1())
        return self._serialize_key_pair(private_key)

    def add_contact(self, name: str, public_key_pem: str) -> Dict[str, str]:
        fingerprint = self.fingerprint(public_key_pem)
        if self.db and getattr(self.db, "conn", None):
            cursor = self.db.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO contacts
                (name, public_key, fingerprint, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (name, public_key_pem, fingerprint, "active", datetime.now(timezone.utc).isoformat()))
            self.db.conn.commit()
        return {"name": name, "public_key": public_key_pem, "fingerprint": fingerprint}

    def revoke_contact(self, fingerprint: str):
        if not self.db or not getattr(self.db, "conn", None):
            return False
        cursor = self.db.conn.cursor()
        cursor.execute(
            "UPDATE contacts SET status='revoked', revoked_at=? WHERE fingerprint=?",
            (datetime.now(timezone.utc).isoformat(), fingerprint)
        )
        self.db.conn.commit()
        return cursor.rowcount > 0

    def fingerprint(self, public_key_pem: str) -> str:
        digest = hashlib.sha256(public_key_pem.encode("utf-8")).hexdigest()
        return ":".join(digest[i:i + 2] for i in range(0, 16, 2))

    def _serialize_key_pair(self, private_key) -> Dict[str, str]:
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        return {
            "private_key": private_pem,
            "public_key": public_pem,
            "fingerprint": self.fingerprint(public_pem),
        }


class QRCodeService:
    def __init__(self, validity_seconds: int = 300):
        self.validity_seconds = validity_seconds

    def build_payload(self, payload_type: str, data: Dict) -> Dict:
        issued_at = int(time.time())
        body = {
            "type": payload_type,
            "issued_at": issued_at,
            "expires_at": issued_at + self.validity_seconds,
            "nonce": str(uuid.uuid4()),
            "data": data,
        }
        body["checksum"] = hashlib.sha256(
            json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return body

    def validate_payload(self, payload: Dict) -> bool:
        checksum = payload.get("checksum")
        unsigned = dict(payload)
        unsigned.pop("checksum", None)
        expected = hashlib.sha256(
            json.dumps(unsigned, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        if checksum != expected:
            return False
        return int(time.time()) <= int(payload.get("expires_at", 0))

    def generate_qr_chunks(self, payload: Dict, chunk_size: int = 1024) -> List[Dict]:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        compressed = zlib.compress(encoded)
        total = max(1, math.ceil(len(compressed) / chunk_size))
        chunks = []
        transfer_id = str(uuid.uuid4())
        for index in range(total):
            chunk = compressed[index * chunk_size:(index + 1) * chunk_size]
            chunks.append({
                "transfer_id": transfer_id,
                "chunk": index + 1,
                "total": total,
                "data": base64.b64encode(chunk).decode("ascii"),
                "checksum": hashlib.sha256(chunk).hexdigest()[:16],
            })
        return chunks

    def decode_qr_chunks(self, chunks: List[Dict]) -> Optional[Dict]:
        try:
            ordered = sorted(chunks, key=lambda item: item["chunk"])
            if not ordered:
                return None
            total = ordered[0]["total"]
            if len(ordered) != total:
                return None

            data_parts = []
            for expected_index, item in enumerate(ordered, start=1):
                if item["chunk"] != expected_index:
                    return None
                chunk = base64.b64decode(item["data"].encode("ascii"))
                if hashlib.sha256(chunk).hexdigest()[:16] != item["checksum"]:
                    return None
                data_parts.append(chunk)

            payload = json.loads(zlib.decompress(b"".join(data_parts)).decode("utf-8"))
            return payload if self.validate_payload(payload) else None
        except Exception:
            return None

    def render_svg_placeholder(self, chunk: Dict, size: int = 320) -> str:
        text = json.dumps(chunk, sort_keys=True)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cell = size // 16
        rects = []
        for row in range(16):
            for col in range(16):
                value = int(digest[(row * 16 + col) % len(digest)], 16)
                if value % 2 == 0:
                    rects.append(f'<rect x="{col * cell}" y="{row * cell}" width="{cell}" height="{cell}" fill="#111"/>')
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}"><rect width="{size}" height="{size}" fill="#fff"/>{"".join(rects)}</svg>'
