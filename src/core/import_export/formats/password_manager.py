import json
from typing import List, Dict


class PasswordManagerFormat:
    def dump_bitwarden(self, entries: List[Dict]) -> Dict:
        items = []
        for entry in entries:
            items.append({
                "type": 1,
                "name": entry.get("title", ""),
                "notes": entry.get("notes", ""),
                "login": {
                    "username": entry.get("username", ""),
                    "password": entry.get("password", ""),
                    "uris": [{"uri": entry.get("url", "")}] if entry.get("url") else [],
                },
                "folderId": entry.get("category", ""),
            })
        return {
            "encrypted": False,
            "folders": [],
            "items": items,
        }

    def load_bitwarden(self, text: str) -> List[Dict]:
        data = json.loads(text)
        entries = []
        for item in data.get("items", []):
            login = item.get("login") or {}
            uris = login.get("uris") or []
            entries.append({
                "title": item.get("name", "Imported entry"),
                "username": login.get("username", ""),
                "password": login.get("password", ""),
                "url": uris[0].get("uri", "") if uris else "",
                "notes": item.get("notes", ""),
                "category": item.get("folderId", ""),
            })
        return entries

    def load_lastpass_csv(self, text: str) -> List[Dict]:
        from src.core.import_export.formats.csv_format import CSVFormat

        entries = CSVFormat().load(text)
        for entry in entries:
            if not entry.get("title") and entry.get("url"):
                entry["title"] = entry["url"]
        return entries
