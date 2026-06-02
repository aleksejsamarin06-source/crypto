import json
from datetime import datetime, timezone
from typing import List, Dict, Any

from src.core.events import event_system
from src.core.import_export.crypto_utils import (
    SOURCE_APPLICATION,
    EXPORT_VERSION,
    canonical_json,
    encrypt_with_password,
    encrypt_with_public_key,
    sha256_hex,
)
from src.core.import_export.formats.csv_format import CSVFormat
from src.core.import_export.formats.password_manager import PasswordManagerFormat


class VaultExporter:
    def __init__(self, entry_manager, db_connection=None):
        self.entry_manager = entry_manager
        self.db = db_connection or getattr(entry_manager, "db", None)

    def export_vault(self, entry_ids: List[int] = None, password: str = None,
                     public_key: bytes = None, export_format: str = "encrypted_json",
                     include_fields: List[str] = None, key_bits: int = 256,
                     compress: bool = False, allow_plaintext: bool = False) -> Any:
        entries = self._get_entries_for_export(entry_ids, include_fields)

        if export_format == "csv":
            csv_text = CSVFormat().dump(entries)
            if allow_plaintext and not password and not public_key:
                self._record_history("export", "csv", len(entries), sha256_hex(csv_text.encode("utf-8")), "success")
                event_system.publish("export_performed", {"format": "csv", "count": len(entries)})
                return csv_text
            self._validate_encryption_material(password, public_key)
            payload = self._build_payload(entries, "csv", csv_text)
            package = encrypt_with_password(payload, password, key_bits, compress) if password else encrypt_with_public_key(payload, public_key, key_bits, compress)
        elif export_format == "bitwarden_json":
            bitwarden_data = PasswordManagerFormat().dump_bitwarden(entries)
            if allow_plaintext and not password and not public_key:
                text = json.dumps(bitwarden_data, ensure_ascii=False, indent=2)
                self._record_history("export", "bitwarden_json", len(entries), sha256_hex(text.encode("utf-8")), "success")
                event_system.publish("export_performed", {"format": "bitwarden_json", "count": len(entries)})
                return bitwarden_data
            self._validate_encryption_material(password, public_key)
            payload = self._build_payload(entries, "bitwarden_json", bitwarden_data)
            package = encrypt_with_password(payload, password, key_bits, compress) if password else encrypt_with_public_key(payload, public_key, key_bits, compress)
        else:
            self._validate_encryption_material(password, public_key)
            payload = self._build_payload(entries, "encrypted_json")
            package = encrypt_with_password(payload, password, key_bits, compress) if password else encrypt_with_public_key(payload, public_key, key_bits, compress)

        package_hash = sha256_hex(canonical_json(package))
        package["package_hash"] = package_hash
        self._record_history("export", export_format, len(entries), package_hash, "success")
        event_system.publish("export_performed", {"format": export_format, "count": len(entries)})
        return package

    def save_export(self, file_path: str, export_data: Any):
        mode = "w"
        with open(file_path, mode, encoding="utf-8", newline="") as file:
            if isinstance(export_data, str):
                file.write(export_data)
            else:
                json.dump(export_data, file, ensure_ascii=False, indent=2)
        return file_path

    def _build_payload(self, entries: List[Dict], payload_format: str, external_data=None) -> Dict[str, Any]:
        payload = {
            "metadata": {
                "version": EXPORT_VERSION,
                "source_application": SOURCE_APPLICATION,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format": payload_format,
                "entry_count": len(entries),
            },
            "entries": entries,
        }
        if external_data is not None:
            payload["external_data"] = external_data
        return payload

    def _get_entries_for_export(self, entry_ids: List[int] = None, include_fields: List[str] = None) -> List[Dict]:
        if entry_ids:
            entries = [self.entry_manager.get_entry(int(entry_id)) for entry_id in entry_ids]
            entries = [entry for entry in entries if entry]
        else:
            entries = self.entry_manager.get_all_entries()

        fields = include_fields or ["id", "title", "username", "password", "url", "domain", "notes", "category", "created_at", "updated_at"]
        filtered = []
        for entry in entries:
            filtered.append({field: entry.get(field, "") for field in fields if field in entry})
        return filtered

    def _record_history(self, operation: str, export_format: str, entry_count: int,
                        package_hash: str, status: str, details: str = "", retry: bool = True):
        if not self.db or not getattr(self.db, "conn", None):
            return
        cursor = self.db.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO import_export_history
                (operation, format, entry_count, package_hash, created_at, status, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                operation, export_format, entry_count, package_hash,
                datetime.now(timezone.utc).isoformat(), status, details
            ))
            self.db.conn.commit()
        except Exception:
            self.db.conn.rollback()
            if retry and hasattr(self.db, "create_tables"):
                self.db.create_tables()
                self._record_history(operation, export_format, entry_count, package_hash, status, details, retry=False)

    def _validate_encryption_material(self, password: str = None, public_key: bytes = None):
        if not password and not public_key:
            raise ValueError("Укажите пароль экспорта или разрешите plaintext для CSV/Bitwarden")
