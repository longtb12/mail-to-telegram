import time;

class TTLIntArray:
    def __init__(self, ttl=86400):
        self.ttl = ttl
        self.data = {}
        
    def _clean_up(self):
        now = time.time()
        expired_keys = [key for key, expiry in self.data.items() if expiry < now]
        for key in expired_keys:
            del self.data[key]

    def add(self, number: int):
        self._clean_up()
        self.data[number] = time.time() + self.ttl

    def exists(self, number: int) -> bool:
        self._clean_up()
        return number in self.data