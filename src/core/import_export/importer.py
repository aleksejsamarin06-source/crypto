import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

from src.core.events import event_system
from src.core.import_export.crypto_utils import (
    canonical_json,
    decrypt_with_password,
    decrypt_with_private_key,
    sha256_hex,
)
from src.core.import_export.formats.csv_format import CSVFormat
from src.core.import_export.formats.password_manager import PasswordManagerFormat


class VaultImporter:
    def __init__(self, entry_manager, db_connection=None, max_file_size: int = 10 * 1024 * 1024,
                 timeout_seconds: int = 30):
        self.entry_manager = entry_manager
        self.db = db_connection or getattr(entry_manager, "db", None)
        self.max_file_size = max_file_size
        self.timeout_seconds = timeout_seconds

    def import_file(self, file_path: str, password: str = None, private_key: bytes = None,
                    import_format: str = None, mode: str = "merge",
                    duplicate_strategy: str = "skip") -> Dict[str, Any]:
        if os.path.getsize(file_path) > self.max_file_size:
            raise ValueError("Import file exceeds size limit")

        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
        return self.import_data(text, password, private_key, import_format, mode, duplicate_strategy)

    def import_data(self, raw_data: Any, password: str = None, private_key: bytes = None,
                    import_format: str = None, mode: str = "merge",
                    duplicate_strategy: str = "skip") -> Dict[str, Any]:
        started = time.time()
        entries = self.parse_entries(raw_data, password, private_key, import_format)
        sanitized = [self.sanitize_entry(entry) for entry in entries]
        self.validate_entries(sanitized)

        summary = self._build_summary(sanitized, duplicate_strategy)
        if mode == "dry-run":
            summary["mode"] = "dry-run"
            return summary

        if mode == "replace":
            self._clear_vault()

        imported = 0
        updated = 0
        skipped = 0
        existing = self._existing_by_title_url()

        for entry in sanitized:
            if time.time() - started > self.timeout_seconds:
                raise TimeoutError("Import processing timed out")

            key = self._entry_key(entry)
            existing_id = existing.get(key)
            if existing_id and duplicate_strategy == "skip":
                skipped += 1
                continue
            if existing_id and duplicate_strategy == "update":
                self.entry_manager.update_entry(existing_id, entry)
                updated += 1
                continue

            self.entry_manager.create_entry(entry)
            imported += 1

        result = {
            "mode": mode,
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "total": len(sanitized),
        }
        self._record_history("import", import_format or "auto", len(sanitized), "success", json.dumps(result))
        event_system.publish("import_performed", result)
        return result

    def parse_entries(self, raw_data: Any, password: str = None, private_key: bytes = None,
                      import_format: str = None) -> List[Dict]:
        if isinstance(raw_data, dict):
            data = raw_data
            text = json.dumps(raw_data, ensure_ascii=False)
        else:
            text = raw_data
            try:
                data = json.loads(text)
            except Exception:
                data = None

        detected = import_format or self.detect_format(text, data)
        if detected == "encrypted_json":
            if not data:
                raise ValueError("Invalid encrypted JSON")
            if data.get("encryption", {}).get("method") == "public_key":
                payload = decrypt_with_private_key(data, private_key)
            else:
                payload = decrypt_with_password(data, password)
            return payload.get("entries", [])
        if detected == "bitwarden_json":
            return PasswordManagerFormat().load_bitwarden(text)
        if detected == "lastpass_csv":
            return PasswordManagerFormat().load_lastpass_csv(text)
        if detected == "csv":
            return CSVFormat().load(text)
        if detected == "native_plain_json":
            return data.get("entries", [])
        raise ValueError("Unsupported import format")

    def detect_format(self, text: str, data=None) -> str:
        if data and isinstance(data, dict):
            if "encryption" in data and "data" in data:
                return "encrypted_json"
            if "items" in data:
                return "bitwarden_json"
            if "entries" in data:
                return "native_plain_json"
        first_line = text.splitlines()[0].lower() if text.splitlines() else ""
        if "url" in first_line and "username" in first_line and "password" in first_line:
            return "lastpass_csv" if "extra" in first_line or "grouping" in first_line else "csv"
        return "csv"

    def sanitize_entry(self, entry: Dict) -> Dict:
        clean = {}
        for key in ["title", "username", "password", "url", "domain", "notes", "category"]:
            value = entry.get(key, "")
            if value is None:
                value = ""
            value = str(value)
            value = re.sub(r"<\s*/?\s*script[^>]*>", "", value, flags=re.IGNORECASE)
            value = re.sub(r"javascript\s*:", "", value, flags=re.IGNORECASE)
            value = "".join(ch for ch in value if ch in "\n\r\t" or ord(ch) >= 32)
            clean[key] = value.strip()
        if not clean["title"]:
            clean["title"] = clean["url"] or clean["username"] or "Imported entry"
        return clean

    def validate_entries(self, entries: List[Dict]):
        for entry in entries:
            if len(entry.get("title", "")) > 255:
                raise ValueError("Entry title is too long")
            if len(entry.get("password", "")) > 4096:
                raise ValueError("Entry password is too long")
            text = json.dumps(entry, ensure_ascii=False).lower()
            if any(pattern in text for pattern in ["<script", "javascript:", ".exe", "powershell -", "cmd.exe"]):
                raise ValueError("Potentially malicious import content")

    def _build_summary(self, entries: List[Dict], duplicate_strategy: str) -> Dict[str, Any]:
        existing = self._existing_by_title_url()
        duplicates = sum(1 for entry in entries if self._entry_key(entry) in existing)
        return {
            "total": len(entries),
            "duplicates": duplicates,
            "new": len(entries) - duplicates,
            "duplicate_strategy": duplicate_strategy,
            "preview": entries[:10],
        }

    def _existing_by_title_url(self) -> Dict[str, int]:
        result = {}
        try:
            for entry in self.entry_manager.get_all_entries():
                result[self._entry_key(entry)] = entry["id"]
        except Exception:
            pass
        return result

    def _entry_key(self, entry: Dict) -> str:
        return (entry.get("title", "").strip().lower() + "|" + entry.get("url", "").strip().lower())

    def _clear_vault(self):
        cursor = self.db.conn.cursor()
        cursor.execute("DELETE FROM vault_entries")
        self.db.conn.commit()

    def _record_history(self, operation: str, import_format: str, entry_count: int,
                        status: str, details: str = "", retry: bool = True):
        if not self.db or not getattr(self.db, "conn", None):
            return
        cursor = self.db.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO import_export_history
                (operation, format, entry_count, package_hash, created_at, status, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                operation, import_format, entry_count, sha256_hex(details.encode("utf-8")),
                datetime.now(timezone.utc).isoformat(), status, details
            ))
            self.db.conn.commit()
        except Exception:
            self.db.conn.rollback()
            if retry and hasattr(self.db, "create_tables"):
                self.db.create_tables()
                self._record_history(operation, import_format, entry_count, status, details, retry=False)
