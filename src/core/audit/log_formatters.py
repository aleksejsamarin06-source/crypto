# src/core/audit/log_formatters.py
import json
import csv
from datetime import datetime
from typing import List, Dict, Any
import os


class LogFormatter:
    def __init__(self, db_connection):
        self.db = db_connection

    def get_all_entries(self) -> List[Dict]:
        """Получение всех записей из лога"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT sequence_number, timestamp, event_type, severity,
                   user_id, source, entry_id, details
            FROM audit_log ORDER BY sequence_number
        """)
        rows = cursor.fetchall()

        entries = []
        for row in rows:
            entries.append({
                'sequence': row[0],
                'timestamp': row[1],
                'event_type': row[2],
                'severity': row[3],
                'user_id': row[4],
                'source': row[5],
                'entry_id': row[6],
                'details': json.loads(row[7]) if row[7] else {}
            })
        return entries

    def export_json(self, file_path: str, include_signatures: bool = True):
        """Экспорт в JSON"""
        entries = self.get_all_entries()

        if include_signatures:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT sequence_number, signature FROM audit_log ORDER BY sequence_number")
            sig_rows = cursor.fetchall()
            sig_dict = {row[0]: row[1] for row in sig_rows}

            for entry in entries:
                entry['signature'] = sig_dict.get(entry['sequence'])

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

        return file_path

    def export_csv(self, file_path: str):
        """Экспорт в CSV"""
        entries = self.get_all_entries()

        if not entries:
            return

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=entries[0].keys())
            writer.writeheader()
            writer.writerows(entries)

        return file_path

    def export_pdf(self, file_path: str):
        """Экспорт в PDF (упрощённый, требует reportlab)"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import mm

            c = canvas.Canvas(file_path, pagesize=A4)
            width, height = A4

            c.setFont("Helvetica", 16)
            c.drawString(20, height - 30, "Отчёт аудита CryptoSafe")

            c.setFont("Helvetica", 10)
            c.drawString(20, height - 50, f"Дата экспорта: {datetime.now().isoformat()}")

            entries = self.get_all_entries()
            y = height - 80

            for entry in entries[-50:]:  # последние 50 записей
                if y < 50:
                    c.showPage()
                    y = height - 50

                text = f"[{entry['timestamp'][:19]}] {entry['event_type']} - {entry['user_id']}"
                c.drawString(20, y, text[:100])
                y -= 15

            c.save()
            return file_path
        except ImportError:
            raise ImportError("Для экспорта в PDF установите reportlab: pip install reportlab")

    def export_signed_json(self, file_path: str, public_key: str = None):
        """Экспорт в подписанный JSON (для внешней верификации)"""
        export_data = {
            'export_metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_entries': 0,
                'public_key': public_key
            },
            'entries': []
        }

        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT sequence_number, timestamp, event_type, severity,
                   user_id, source, entry_id, details, signature
            FROM audit_log ORDER BY sequence_number
        """)
        rows = cursor.fetchall()

        for row in rows:
            export_data['entries'].append({
                'sequence': row[0],
                'timestamp': row[1],
                'event_type': row[2],
                'severity': row[3],
                'user_id': row[4],
                'source': row[5],
                'entry_id': row[6],
                'details': json.loads(row[7]) if row[7] else {},
                'signature': row[8]
            })

        export_data['export_metadata']['total_entries'] = len(export_data['entries'])

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        return file_path
