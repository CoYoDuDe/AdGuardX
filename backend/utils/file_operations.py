import os
import json
import logging

logger = logging.getLogger(__name__)

def sicher_speichern(pfad, inhalt, is_json=False):
    """Speichert Inhalte sicher in einer Datei."""
    try:
        with open(pfad, "w") as file:
            if is_json:
                json.dump(inhalt, file, indent=4)
            else:
                file.write(inhalt)
        logger.info(f"Datei erfolgreich gespeichert: {pfad}")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Datei {pfad}: {e}")

def lade_datei(pfad, default_inhalt=None):
    """Lädt eine Datei, falls vorhanden, oder gibt Standardinhalt zurück."""
    if os.path.exists(pfad):
        with open(pfad, "r") as file:
            return json.load(file) if pfad.endswith(".json") else file.read()
    return default_inhalt
