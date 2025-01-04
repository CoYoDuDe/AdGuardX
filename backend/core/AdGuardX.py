#!/usr/bin/env python3

import os
import logging
from backend.config import lade_konfiguration, initialisiere_verzeichnisse_und_dateien
from backend.dns_utils import erstelle_dnsmasq_conf, teste_domains_batch
from backend.stats import aktualisiere_gesamtstatistik, bewerte_listen
from backend.utils import lade_whitelist, lade_blacklist

# Globale Variablen
CONFIG = {}
LOG_FILE = "adblock.log"

def hauptprozess():
    logging.info("Starte AdGuardX Hauptprozess")

    # Initialisierung
    initialisiere_verzeichnisse_und_dateien()
    CONFIG.update(lade_konfiguration())
    logging.info("Konfiguration geladen")

    # Domains extrahieren und testen
    whitelist = lade_whitelist()
    blacklist = lade_blacklist()
    domains = {"example.com", "test.com"}  # Platzhalter für spätere dynamische Listen
    domains = domains - whitelist
    domains = domains | blacklist

    # Testen der Domains
    getestete_domains = teste_domains_batch(domains)
    logging.info(f"{len(getestete_domains)} Domains getestet")

    # DNS-Konfiguration erstellen
    erreichbare_domains = {d for d, erreichbar in getestete_domains.items() if erreichbar}
    erstelle_dnsmasq_conf(erreichbare_domains)

    # Statistiken aktualisieren
    aktualisiere_gesamtstatistik()

    logging.info("Hauptprozess abgeschlossen")


if __name__ == "__main__":
    # Logging konfigurieren
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", filename=LOG_FILE)

    try:
        hauptprozess()
    except Exception as e:
        logging.error(f"Fehler im Hauptprozess: {e}")
