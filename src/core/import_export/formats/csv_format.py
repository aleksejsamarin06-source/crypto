import csv
import io
from typing import List, Dict


class CSVFormat:
    fields = ["title", "username", "password", "url", "notes", "category"]

    def dump(self, entries: List[Dict]) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.fields, extrasaction="ignore")
        writer.writeheader()
        for entry in entries:
            writer.writerow({field: entry.get(field, "") for field in self.fields})
        return output.getvalue()

    def load(self, text: str) -> List[Dict]:
        sample = text[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        entries = []
        for row in reader:
            entries.append({
                "title": row.get("title") or row.get("name") or row.get("url") or "Imported entry",
                "username": row.get("username") or row.get("login") or "",
                "password": row.get("password") or "",
                "url": row.get("url") or row.get("website") or "",
                "notes": row.get("notes") or row.get("note") or "",
                "category": row.get("category") or row.get("folder") or "",
            })
        return entries
