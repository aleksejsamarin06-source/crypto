import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from src.core.events import event_system
from src.core.import_export.crypto_utils import (
    canonical_json,
    decrypt_with_password,
    decrypt_with_private_key,
    encrypt_with_password,
    encrypt_with_public_key,
    sha256_hex,
)


class SharingService:
    def __init__(self, entry_manager, db_connection=None):
        self.entry_manager = entry_manager
        self.db = db_connection or getattr(entry_manager, "db", None)

    def share_entry(self, entry_id: int, recipient: str, password: str = None,
                    public_key: bytes = None, permissions: Dict[str, Any] = None,
                    expires_in_days: int = 7, expires_in_minutes: int = None) -> Dict[str, Any]:
        if not password and not public_key:
            raise ValueError("Sharing requires password or public_key")
        if expires_in_minutes is None:
            if expires_in_days < 1 or expires_in_days > 30:
                raise ValueError("Expiration must be between 1 and 30 days")
            expires_delta = timedelta(days=expires_in_days)
        else:
            if expires_in_minutes < 1 or expires_in_minutes > 30 * 24 * 60:
                raise ValueError("Expiration must be between 1 minute and 30 days")
            expires_delta = timedelta(minutes=expires_in_minutes)

        entry = self.entry_manager.get_entry(int(entry_id))
        if not entry:
            raise ValueError("Entry not found")

        permissions = permissions or {"read": True, "edit": False}
        share_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + expires_delta
        limited_entry = self._filter_entry(entry, permissions)
        payload = {
            "metadata": {
                "version": "1.0",
                "source_application": "CryptoSafe Manager",
                "type": "shared_entry",
                "share_id": share_id,
                "recipient": recipient,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": expires_at.isoformat(),
                "permissions": permissions,
            },
            "entries": [limited_entry],
        }

        if password:
            package = encrypt_with_password(payload, password, 256, False)
            method = "password"
        else:
            package = encrypt_with_public_key(payload, public_key, 256, False)
            method = "public_key"
        package["metadata"]["type"] = "shared_entry"
        package["metadata"]["share_id"] = share_id

        package_hash = sha256_hex(canonical_json(package))
        self._record_share(share_id, entry_id, recipient, permissions, method, package_hash, expires_at)
        event_system.publish("entry_shared", {"id": entry_id, "recipient": recipient, "share_id": share_id})
        return {
            "share_id": share_id,
            "expires_at": expires_at.isoformat(),
            "permissions": permissions,
            "package": package,
            "package_hash": package_hash,
        }

    def import_shared_entry(self, package: Dict[str, Any], password: str = None,
                            private_key: bytes = None, save_to_vault: bool = True) -> Dict[str, Any]:
        if package.get("encryption", {}).get("method") == "public_key":
            payload = decrypt_with_private_key(package, private_key)
        else:
            payload = decrypt_with_password(package, password)

        metadata = payload.get("metadata", {})
        expires_at = metadata.get("expires_at")
        if expires_at and datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
            raise ValueError("Share package has expired")

        entries = payload.get("entries", [])
        if not entries:
            raise ValueError("Share package has no entry")

        entry = entries[0]
        result = {"entry": entry, "saved": False}
        if save_to_vault:
            entry_id = self.entry_manager.create_entry(entry)
            result["saved"] = True
            result["entry_id"] = entry_id
        event_system.publish("shared_entry_imported", {"share_id": metadata.get("share_id"), "saved": result["saved"]})
        return result

    def _filter_entry(self, entry: Dict, permissions: Dict[str, Any]) -> Dict:
        fields = ["title", "username", "password", "url", "notes", "category"]
        if permissions.get("exclude_notes"):
            fields.remove("notes")
        return {field: entry.get(field, "") for field in fields}

    def _record_share(self, share_id: str, entry_id: int, recipient: str,
                      permissions: Dict[str, Any], method: str,
                      package_hash: str, expires_at: datetime):
        if not self.db or not getattr(self.db, "conn", None):
            return
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO shared_entries
            (share_id, original_entry_id, recipient, permissions, encryption_method,
             package_hash, expires_at, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            share_id, entry_id, recipient, json.dumps(permissions, ensure_ascii=False),
            method, package_hash, expires_at.isoformat(),
            datetime.now(timezone.utc).isoformat(), "active"
        ))
        self.db.conn.commit()
