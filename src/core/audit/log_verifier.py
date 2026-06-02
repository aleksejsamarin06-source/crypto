# src/core/audit/log_verifier.py
import json
import hashlib
from datetime import datetime
from typing import Dict, Any
from src.core.audit.log_signer import AuditLogSigner


class LogVerifier:
    def __init__(self, db_connection, master_password: str = None):
        self.db = db_connection
        self.signer = AuditLogSigner(master_password) if master_password else None

    def reconstruct_entry_data(self, row):
        """Восстановление entry_data из БД (сначала пробуем entry_data)"""
        entry_data_str = row[-1] if len(row) > 11 else None

        if entry_data_str:
            return json.loads(entry_data_str)

        # fallback для старых записей (если нет entry_data)
        (seq_num, timestamp, event_type, severity, user_id,
         source, entry_id, details, previous_hash, entry_hash, signature_hex) = row[:11]

        try:
            details_dict = json.loads(details) if details else {}
        except:
            details_dict = {'raw': details}

        return {
            'sequence_number': seq_num,
            'timestamp': timestamp,
            'event_type': event_type,
            'severity': severity,
            'user_id': user_id,
            'source': source,
            'entry_id': entry_id,
            'details': details_dict,
            'previous_hash': previous_hash,
            'entry_hash': entry_hash,
            'signature': signature_hex
        }

    def verify_full(self) -> Dict[str, Any]:
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT sequence_number, timestamp, event_type, severity, user_id,
                   source, entry_id, details, previous_hash, entry_hash, signature, entry_data
            FROM audit_log ORDER BY sequence_number
        """)
        rows = cursor.fetchall()

        results = {
            'total': len(rows),
            'valid_signatures': 0,
            'invalid_signatures': [],
            'chain_breaks': [],
            'is_valid': True
        }

        previous_hash = None

        for row in rows:
            entry_data = self.reconstruct_entry_data(row)
            seq_num = entry_data.get('sequence_number', 0)
            stored_hash = entry_data.get('entry_hash', '')
            prev_hash = entry_data.get('previous_hash', '')
            signature_hex = entry_data.get('signature', '')

            entry_json = json.dumps(
                {k: v for k, v in entry_data.items() if k != 'signature'},
                sort_keys=True,
                ensure_ascii=False
            ).encode('utf-8')

            # Проверка подписи
            if self.signer and signature_hex:
                try:
                    signature = bytes.fromhex(signature_hex)
                    if self.signer.verify(entry_json, signature):
                        results['valid_signatures'] += 1
                    else:
                        results['invalid_signatures'].append(seq_num)
                        results['is_valid'] = False
                except Exception as e:
                    results['invalid_signatures'].append(seq_num)
                    results['is_valid'] = False
            else:
                print(f" Запись {seq_num}: signer={self.signer is not None}, signature_hex={bool(signature_hex)}")

            # Проверка хеш-цепочки
            if previous_hash is not None and prev_hash != previous_hash:
                results['chain_breaks'].append({
                    'sequence': seq_num,
                    'expected': previous_hash,
                    'actual': prev_hash
                })
                results['is_valid'] = False

            previous_hash = stored_hash

        return results

    def verify_range(self, start_seq: int, end_seq: int) -> Dict[str, Any]:
        """Проверка диапазона записей"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT sequence_number, timestamp, event_type, severity, user_id,
                   source, entry_id, details, previous_hash, entry_hash, signature, entry_data
            FROM audit_log
            WHERE sequence_number BETWEEN ? AND ?
            ORDER BY sequence_number
        """, (start_seq, end_seq))
        rows = cursor.fetchall()

        results = {
            'total': len(rows),
            'valid_signatures': 0,
            'invalid_signatures': [],
            'is_valid': True
        }

        for row in rows:
            entry_data = self.reconstruct_entry_data(row)
            seq_num = entry_data.get('sequence_number', 0)
            signature_hex = entry_data.get('signature', '')

            entry_json = json.dumps(
                {k: v for k, v in entry_data.items() if k not in ['signature', 'entry_hash']},
                sort_keys=True,
                ensure_ascii=False
            ).encode('utf-8')

            if self.signer and signature_hex:
                try:
                    signature = bytes.fromhex(signature_hex)
                    if self.signer.verify(entry_json, signature):
                        results['valid_signatures'] += 1
                    else:
                        results['invalid_signatures'].append(seq_num)
                        results['is_valid'] = False
                except:
                    results['invalid_signatures'].append(seq_num)
                    results['is_valid'] = False

        return results

    def check_integrity(self) -> bool:
        """Быстрая проверка целостности (последняя запись)"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM audit_log")
        count = cursor.fetchone()[0]

        if count == 0:
            return True

        cursor.execute("""
            SELECT sequence_number, timestamp, event_type, severity, user_id,
                   source, entry_id, details, previous_hash, entry_hash, signature, entry_data
            FROM audit_log ORDER BY sequence_number DESC LIMIT 1
        """)
        row = cursor.fetchone()

        if not row:
            return False

        entry_data_str = row[-1] if len(row) > 11 else None

        if entry_data_str:
            entry_data = json.loads(entry_data_str)
            stored_hash = entry_data.get('entry_hash', '')
        else:
            stored_hash = row[9] if len(row) > 9 else ''

        return len(stored_hash) > 0

    def get_verification_report(self) -> str:
        """Получение отчёта о проверке в читаемом виде"""
        result = self.verify_full()

        report = []
        report.append("=" * 50)
        report.append("ОТЧЁТ О ПРОВЕРКЕ ЦЕЛОСТНОСТИ ЛОГА")
        report.append("=" * 50)
        report.append(f"Всего записей: {result['total']}")
        report.append(f"Подписи верны: {result['valid_signatures']}/{result['total']}")

        if result['invalid_signatures']:
            report.append(f"\nНекорректные подписи: {result['invalid_signatures']}")

        if result['chain_breaks']:
            report.append(f"\nРазрывы хеш-цепочки: {result['chain_breaks']}")

        report.append(f"\nЦелостность: {'НАРУШЕНА' if not result['is_valid'] else 'ПОДТВЕРЖДЕНА'}")
        report.append("=" * 50)

        return "\n".join(report)

    def verify_and_notify(self) -> bool:
        """Проверка с уведомлением о нарушениях"""
        result = self.verify_full()

        if not result['is_valid']:
            from src.core.events import event_system
            event_system.publish('log_tampering_detected', {
                'invalid_signatures': result['invalid_signatures'],
                'chain_breaks': result['chain_breaks'],
                'timestamp': datetime.now().isoformat()
            })
            return False
        return True
