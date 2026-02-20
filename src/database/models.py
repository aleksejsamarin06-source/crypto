import datetime


class VaultEntry:
    def __init__(self, id=None, title=None, username=None, password=None, url=None, notes=None):
        self.id = id
        self.title = title
        self.username = username
        self.password = password
        self.url = url
        self.notes = notes

class AuditLog:
    def __init__(self, id=None, action=None, timestamp=None, entry_id=None, details=None):
        self.id = id
        self.action = action
        self.timestamp = timestamp
        self.entry_id = entry_id
        self.details = details

class AuditLog:
    def __init__(self, id=None, action=None, entry_id=None, details=None, signature=None):
        self.id = id
        self.action = action
        self.timestamp = datetime.datetime.now()
        self.entry_id = entry_id
        self.details = details
        self.signature = signature  