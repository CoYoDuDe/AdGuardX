import os
import json

class ConfigUtils:
    DEFAULT_CONFIG = {
        "log_datei": "adblock.log",
        "dns_server_list": ["8.8.8.8", "1.1.1.1"],
        "max_parallel_jobs": 5,
        "retry_delay": 2,
        "domain_timeout": 5,
        "send_email": False,
        "email": "",
    }

    @staticmethod
    def lade_konfiguration(config_path="config.json"):
        """
        Lädt die Konfigurationsdatei oder erstellt eine Standardkonfiguration, falls die Datei fehlt.
        :param config_path: Pfad zur Konfigurationsdatei
        :return: Geladene oder Standardkonfiguration
        """
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as file:
                    return json.load(file)
            except json.JSONDecodeError:
                print(f"Fehler beim Lesen der Konfigurationsdatei {config_path}.")
        # Standardkonfiguration speichern
        ConfigUtils.speichere_konfiguration(ConfigUtils.DEFAULT_CONFIG, config_path)
        return ConfigUtils.DEFAULT_CONFIG

    @staticmethod
    def speichere_konfiguration(config, config_path="config.json"):
        """
        Speichert die Konfiguration in eine Datei.
        :param config: Die zu speichernde Konfiguration
        :param config_path: Pfad zur Konfigurationsdatei
        """
        try:
            with open(config_path, 'w') as file:
                json.dump(config, file, indent=4)
            print(f"Konfiguration gespeichert: {config_path}")
        except Exception as e:
            print(f"Fehler beim Speichern der Konfiguration: {e}")
