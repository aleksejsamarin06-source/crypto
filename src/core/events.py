class EventSystem:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event, callback):
        if event not in self.subscribers:
            self.subscribers[event] = []
        self.subscribers[event].append(callback)

    def publish(self, event, data=None):
        if event in self.subscribers:
            for callback in self.subscribers[event]:
                callback(data)

event_system = EventSystem()