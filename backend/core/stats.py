from collections import defaultdict
import json
import os

class Statistics:
    def __init__(self, stats_file="tmp/statistik.json"):
        self.stats_file = stats_file
        self.stats = {
            "getestete_domains": 0,
            "erreichbare_domains": 0,
            "nicht_erreichbare_domains": 0,
            "fehlerhafte_lists": 0,
            "gesamt_domains": 0,
            "duplikate": 0,
            "duplikate_pro_liste": defaultdict(int),
            "nicht_erreichbare_pro_liste": defaultdict(int),
            "erreichbare_pro_liste": defaultdict(int),
            "gesamtstatistik": [],
        }
        self._lade_statistiken()

    def _lade_statistiken(self):
        """Lädt die Statistiken aus einer Datei, wenn sie existiert."""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as file:
                    self.stats = json.load(file)
            except (json.JSONDecodeError, IOError):
                print("Warnung: Statistikdatei beschädigt oder nicht lesbar. Starte mit leeren Statistiken.")
    
    def speichere_statistiken(self):
        """Speichert die aktuellen Statistiken in die Datei."""
        try:
            with open(self.stats_file, 'w') as file:
                json.dump(self.stats, file, indent=4)
        except IOError as e:
            print(f"Fehler beim Speichern der Statistikdatei: {e}")
    
    def aktualisiere_statistik(self, key, value):
        """Aktualisiert einen bestimmten Statistikwert."""
        if key in self.stats:
            self.stats[key] += value
        else:
            print(f"Warnung: Schlüssel {key} nicht in den Statistiken vorhanden.")

    def add_to_list_stat(self, list_name, key, value):
        """Fügt einen Wert zu einer spezifischen Listenstatistik hinzu."""
        if key == "duplikate":
            self.stats["duplikate_pro_liste"][list_name] += value
        elif key == "nicht_erreichbare":
            self.stats["nicht_erreichbare_pro_liste"][list_name] += value
        elif key == "erreichbare":
            self.stats["erreichbare_pro_liste"][list_name] += value

    def get_summary(self):
        """Gibt eine zusammenfassende Übersicht der Statistiken zurück."""
        return {
            "getestete_domains": self.stats["getestete_domains"],
            "erreichbare_domains": self.stats["erreichbare_domains"],
            "nicht_erreichbare_domains": self.stats["nicht_erreichbare_domains"],
            "fehlerhafte_lists": self.stats["fehlerhafte_lists"],
            "gesamt_domains": self.stats["gesamt_domains"],
            "duplikate": self.stats["duplikate"],
        }
