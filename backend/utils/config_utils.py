import os
import json

STANDARD_CONFIG = {
    "log_datei": "adblock.log",
    "dns_server_list": ["8.8.8.8", "1.1.1.1"],
    "max_parallel_jobs": 5,
    "retry_delay": 2,
    "domain_timeout": 5
}

def lade_konfiguration(config_path="config.json"):
    """
    Lädt die Konfigurationsdatei oder erstellt eine Standardkonfiguration, falls keine vorhanden ist.
    
    :param config_path: Pfad zur Konfigurationsdatei
    :return: Die geladene oder Standardkonfiguration als Dictionary
    """
    if os.path.exists(config_path):
        with open(config_path, 'r') as file:
            return json.load(file)
    else:
        with open(config_path, 'w') as file:
            json.dump(STANDARD_CONFIG, file, indent=4)
        return STANDARD_CONFIG

def initialisiere_verzeichnisse_und_dateien():
    """
    Erstellt notwendige Verzeichnisse und stellt sicher, dass sie existieren.
    """
    os.makedirs("tmp", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("frontend/templates", exist_ok=True)
    os.makedirs("frontend/static", exist_ok=True)
