class EventSystem:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event, callback):
        if event not in self.subscribers:
            self.subscribers[event] = []
        self.subscribers[event].append(callback)

    def publish(self, event, data=None):
        if event in self.subscribers:
            for callback in list(self.subscribers[event]):
                try:
                    callback(data)
                except Exception as e:
                    print(f"Ошибка обработчика события {event}: {e}")

    def clear(self):
        self.subscribers = {}

event_system = EventSystem()
