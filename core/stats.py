
# Statistics Module
# Tracks request statistics and efficiency of filters.

class Statistics:
    def __init__(self):
        self.blocked_requests = 0
        self.allowed_requests = 0

    def log_blocked(self):
        self.blocked_requests += 1

    def log_allowed(self):
        self.allowed_requests += 1

    def get_stats(self):
        return {
            "blocked_requests": self.blocked_requests,
            "allowed_requests": self.allowed_requests,
        }
