
# Konfigurationslogik
CONFIG = {
    "dns_servers": ["8.8.8.8", "1.1.1.1"],
    "max_jobs": 10
}

def update_config(new_config):
    global CONFIG
    CONFIG.update(new_config)
