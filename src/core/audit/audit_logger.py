# src/core/audit/audit_logger.py
import json
import hashlib
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from src.core.events import event_system
from src.core.audit.log_signer import AuditLogSigner


class AuditLogger:
    def __init__(self, db_connection, master_password: str = None):
        self.db = db_connection
        self.signer = AuditLogSigner(master_password)
        self.enabled = True
        self.init_log_structure()
        self.subscribe_to_events()

    def subscribe_to_events(self):
        # Не подписываемся в тестовой среде
        if os.environ.get('UNITTEST_RUNNING') == '1':
            return
        if not self.enabled:
            return
        event_system.subscribe('user_logged_in', lambda d: self.log_auth_event('LOGIN_SUCCESS', d))
        event_system.subscribe('user_logged_out', lambda d: self.log_auth_event('LOGOUT', d))
        event_system.subscribe('entry_added', lambda d: self.log_vault_event('ENTRY_CREATED', d))
        event_system.subscribe('entry_updated', lambda d: self.log_vault_event('ENTRY_UPDATED', d))
        event_system.subscribe('entry_deleted', lambda d: self.log_vault_event('ENTRY_DELETED', d))
        event_system.subscribe('ClipboardCopied', lambda d: self.log_clipboard_event('CLIPBOARD_COPIED', d))
        event_system.subscribe('ClipboardCleared', lambda d: self.log_clipboard_event('CLIPBOARD_CLEARED', d))
        event_system.subscribe('ClipboardSuspicious', lambda d: self.log_security_event('SUSPICIOUS_ACTIVITY', d))
        event_system.subscribe('export_performed', lambda d: self.log_event('EXPORT', 'INFO', 'audit', d, 'user'))
        event_system.subscribe('import_performed', lambda d: self.log_event('IMPORT', 'INFO', 'import_export', d, 'user'))
        event_system.subscribe('entry_shared', lambda d: self.log_event('ENTRY_SHARED', 'INFO', 'sharing', d, 'user', d.get('id') if d else None))
        event_system.subscribe('shared_entry_imported', lambda d: self.log_event('SHARED_ENTRY_IMPORTED', 'INFO', 'sharing', d, 'user'))

    def init_log_structure(self):
        if not self.enabled:
            return
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM audit_log")
        count = cursor.fetchone()[0]

        if count == 0:
            genesis_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': 'SYSTEM_GENESIS',
                'severity': 'INFO',
                'user_id': 'system',
                'source': 'audit_logger',
                'entry_id': None,
                'details': json.dumps({'message': 'Audit log initialized'})
            }
            self.write_entry(genesis_entry, '0' * 64)

    def get_next_sequence(self) -> int:
        if not self.enabled:
            return 0
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT MAX(sequence_number) FROM audit_log")
        max_seq = cursor.fetchone()[0]
        return (max_seq or 0) + 1

    def get_previous_hash(self) -> str:
        if not self.enabled:
            return '0' * 64
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT entry_hash FROM audit_log ORDER BY sequence_number DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else '0' * 64

    def write_entry(self, entry: Dict[str, Any], previous_hash: str = None):
        if not self.enabled:
            return
        if previous_hash is None:
            previous_hash = self.get_previous_hash()

        sequence = self.get_next_sequence()

        entry_data = {
            'sequence_number': sequence,
            'timestamp': entry['timestamp'],
            'event_type': entry['event_type'],
            'severity': entry['severity'],
            'user_id': entry['user_id'],
            'source': entry['source'],
            'entry_id': entry.get('entry_id'),
            'details': entry['details'],
            'previous_hash': previous_hash
        }

        entry_json = json.dumps(entry_data, sort_keys=True, ensure_ascii=False)
        entry_hash = hashlib.sha256(entry_json.encode('utf-8')).hexdigest()

        # Вычисляем подпись
        signature_bytes = self.signer.sign(entry_json.encode('utf-8'))
        signature_hex = signature_bytes.hex()

        # Добавляем хеш и подпись в данные
        entry_data_with_hash = json.loads(entry_json)
        entry_data_with_hash['entry_hash'] = entry_hash
        entry_data_with_hash['signature'] = signature_hex
        entry_json_with_hash = json.dumps(entry_data_with_hash, sort_keys=True, ensure_ascii=False)

        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log
            (sequence_number, timestamp, event_type, severity, user_id, source,
             entry_id, details, previous_hash, entry_hash, signature, entry_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sequence, entry['timestamp'], entry['event_type'], entry['severity'],
            entry['user_id'], entry['source'], entry.get('entry_id'),
            entry['details'], previous_hash, entry_hash, signature_hex,
            entry_json_with_hash
        ))
        self.db.conn.commit()

    def log_event(self, event_type: str, severity: str, source: str,
                  details: Dict, user_id: str = 'anonymous', entry_id: int = None):
        if not self.enabled:
            return
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': event_type,
            'severity': severity,
            'user_id': user_id,
            'source': source,
            'entry_id': entry_id,
            'details': json.dumps(details, ensure_ascii=False)
        }
        self.write_entry(entry)

    def log_auth_event(self, event_type: str, data: dict):
        if not self.enabled:
            return
        user_id = data.get('user_id', 'unknown')
        self.log_event(f'AUTH_{event_type}', 'INFO', 'authentication',
                       {'action': event_type}, user_id)

    def log_vault_event(self, event_type: str, data: dict):
        if not self.enabled:
            return
        entry_id = data.get('id')
        title = data.get('title', '')
        self.log_event(f'VAULT_{event_type}', 'INFO', 'vault',
                       {'action': event_type, 'title': title[:50]}, 'user', entry_id)

    def log_clipboard_event(self, event_type: str, data: dict):
        if not self.enabled:
            return
        self.log_event(event_type, 'INFO', 'clipboard',
                       {'action': event_type, 'source_entry': data.get('source_entry_id')}, 'user')

    def log_security_event(self, event_type: str, data: dict):
        if not self.enabled:
            return
        self.log_event(f'SECURITY_{event_type}', 'WARNING', 'security',
                       {'action': event_type, 'details': data}, 'user')

    def log_settings_change(self, setting_key: str, old_value: str, new_value: str):
        if not self.enabled:
            return
        self.log_event('SETTINGS_CHANGED', 'INFO', 'settings',
                       {'key': setting_key, 'old': old_value, 'new': new_value}, 'user')

    def disable(self):
        self.enabled = False

    def enable(self):
        self.enabled = True
