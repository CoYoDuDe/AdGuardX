import os
import json

class FileUtils:
    @staticmethod
    def sicher_speichern(dateipfad, inhalt, is_json=False):
        """
        Sicheres Speichern in eine Datei mit Fehlerbehandlung.
        :param dateipfad: Pfad zur Datei
        :param inhalt: Der Inhalt (String oder Python-Datenstruktur)
        :param is_json: Gibt an, ob der Inhalt als JSON gespeichert werden soll
        """
        try:
            with open(dateipfad, 'w') as file:
                if is_json:
                    json.dump(inhalt, file, indent=4)
                else:
                    file.write(inhalt)
            print(f"Datei erfolgreich gespeichert: {dateipfad}")
        except Exception as e:
            print(f"Fehler beim Speichern der Datei {dateipfad}: {e}")

    @staticmethod
    def lade_datei(dateipfad, is_json=False):
        """
        Lädt den Inhalt einer Datei.
        :param dateipfad: Pfad zur Datei
        :param is_json: Gibt an, ob die Datei als JSON gelesen werden soll
        :return: Der Inhalt der Datei
        """
        try:
            with open(dateipfad, 'r') as file:
                return json.load(file) if is_json else file.read()
        except FileNotFoundError:
            print(f"Datei {dateipfad} nicht gefunden.")
            return None
        except Exception as e:
            print(f"Fehler beim Laden der Datei {dateipfad}: {e}")
            return None

    @staticmethod
    def erstelle_verzeichnisse(verzeichnisse):
        """
        Erstellt mehrere Verzeichnisse, falls sie nicht existieren.
        :param verzeichnisse: Liste von Verzeichnispfaden
        """
        for verzeichnis in verzeichnisse:
            os.makedirs(verzeichnis, exist_ok=True)
            print(f"Verzeichnis überprüft/erstellt: {verzeichnis}")

    @staticmethod
    def bereinige_obsolete_dateien(verzeichnis, gültige_dateien):
        """
        Entfernt Dateien in einem Verzeichnis, die nicht mehr gültig sind.
        :param verzeichnis: Pfad zum Verzeichnis
        :param gültige_dateien: Liste der gültigen Dateien
        """
        try:
            for datei in os.listdir(verzeichnis):
                dateipfad = os.path.join(verzeichnis, datei)
                if datei not in gültige_dateien and os.path.isfile(dateipfad):
                    os.remove(dateipfad)
                    print(f"Obsolete Datei gelöscht: {dateipfad}")
        except Exception as e:
            print(f"Fehler beim Bereinigen des Verzeichnisses {verzeichnis}: {e}")
