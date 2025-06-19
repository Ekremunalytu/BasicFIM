from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

class FileMonitor:
    def __init__(self, rules):
        self.rules = rules
        self.observer = Observer()
    
    def start(self):
        for rule in self.rules:
            path = rule.get('path')
            if path:
                event_handler = FileSystemEventHandler()
                event_handler.on_modified = self.on_modified
                self.observer.schedule(event_handler, path, recursive=True)
        
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()
