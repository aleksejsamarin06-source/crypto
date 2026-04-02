class StateManager:
    def __init__(self):
        self.is_locked = True
        self.current_user = None
        self.clipboard_content = None
        self.inactivity_time = 0

    def lock(self):
        self.is_locked = True

    def unlock(self, user):
        self.is_locked = False
        self.current_user = user
