#!/usr/bin/env python3

# =============================================================================
# 1. GLOBALE KONFIGURATION UND INITIALISIERUNG
# =============================================================================

import os
import time
import subprocess
import hashlib
import requests
import re
import logging
from logging.handlers import RotatingFileHandler
from multiprocessing import Pool
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import json
from collections import defaultdict
import random
import filecmp
import dns.resolver
from threading import Lock

# Globale Variablen und Lock für Threads
CONFIG = {}
DNS_CACHE = {}
dns_cache_lock = Lock()
STATISTIK = {
    "getestete_domains": 0,
    "erreichbare_domains": 0,
    "nicht_erreichbare_domains": 0,
    "fehlerhafte_lists": 0,
    "gesamt_domains": 0,
    "durchlauf_fehlgeschlagen": False,
    "fehlermeldung": "",
    "duplikate": 0,
    "duplikate_pro_liste": defaultdict(int),
    "nicht_erreichbare_pro_liste": defaultdict(int),
    "erreichbare_pro_liste": defaultdict(int),
    "gesamtstatistik": [],
    "list_bewertung": []
}

# Logging-Konfiguration
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# Standardkonfiguration erstellen
STANDARD_CONFIG = {
    "log_datei": "/var/log/adguardx.log",
    "send_email": True,
    "email": "example@example.com",
    "email_absender": "no-reply@example.com",
    "max_retries": 3,
    "retry_delay": 5,
    "parallel_aktiviert": True,
    "max_parallel_jobs": 1,
    "batching_aktiviert": True,
    "batch_größe": 1000,
    "dns_konfiguration": "/etc/dnsmasq.d/adguardx.conf",
    "verwende_adblock_conf": True,
    "web_server_ipv4": "127.0.0.1",
    "web_server_ipv6": "::1",
    "github_upload": False,
    "github_repo": "git@github.com:example/repo.git",
    "github_branch": "main",
    "git_user": "",
    "git_email": "",
    "dns_server_list": [
        "8.8.8.8",
        "8.8.4.4",
        "1.1.1.1",
        "1.0.0.1",
        "9.9.9.9",
        "149.112.112.112",
        "2001:4860:4860::8888",
        "2001:4860:4860::8844",
        "2606:4700:4700::1111",
        "2606:4700:4700::1001"
    ],
    "logging_level": "INFO",
    "progress_log_frequency": 1000,
    "detailed_log": False,
    "speichere_nicht_erreichbare": True,
    "priorisiere_listen": True,
    "domain_timeout": 5
}

# Standardinhalt für die Hosts-Quellen
STANDARD_HOSTS_SOURCES = """https://example.com/hosts1
https://example.com/hosts2"""

# Bestimmen des Verzeichnisses, in dem sich das Skript befindet
skript_verzeichnis = os.path.dirname(os.path.realpath(__file__))

# =============================================================================
# 2. GIT UND SSH-SCHLÜSSEL MANAGEMENT
# =============================================================================

def setup_git():
    """Überprüft und richtet Git ein, falls erforderlich."""
    if not os.path.exists(os.path.join(skript_verzeichnis, '.git')):
        try:
            subprocess.run(['git', '--version'], check=True)

            user_name = CONFIG.get('git_user', "")
            user_email = CONFIG.get('git_email', "")

            if not user_name or not user_email:
                print("Git-Konfiguration erforderlich. Bitte geben Sie die folgenden Informationen ein:")
                user_name = input("Git-Benutzername: ")
                user_email = input("Git-E-Mail: ")
                CONFIG['git_user'] = user_name
                CONFIG['git_email'] = user_email
                with open(os.path.join(skript_verzeichnis, 'config.json'), 'w') as config_file:
                    json.dump(CONFIG, config_file, indent=4)

            subprocess.run(['git', 'config', '--global', 'user.name', user_name], check=True)
            subprocess.run(['git', 'config', '--global', 'user.email', user_email], check=True)

            ssh_key_path = os.path.expanduser('~/.ssh/adblock_rsa')

            if not os.path.exists(ssh_key_path):
                log("Erstelle neuen SSH-Schlüssel")
                subprocess.run(['ssh-keygen', '-t', 'rsa', '-b', 4096, '-C', user_email, '-N', '', '-f', ssh_key_path], check=True)
                with open(ssh_key_path + '.pub') as pubkey_file:
                    pubkey = pubkey_file.read()
                log(f"SSH-Schlüssel erstellt: {pubkey}")
                print(f"Fügen Sie den folgenden SSH-Schlüssel zu Ihrem GitHub-Konto hinzu:\n{pubkey}")
                print("Starten Sie das Skript neu, nachdem Sie den Schlüssel hinzugefügt haben.")
                exit(0)

            agent_status = subprocess.run(['ssh-add', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if b'adblock_rsa' not in agent_status.stdout:
                if 'SSH_AUTH_SOCK' not in os.environ:
                    agent_output = subprocess.check_output(['ssh-agent', '-s']).decode('utf-8')
                    agent_pid = re.search(r'Agent pid (\d+)', agent_output).group(1)
                    subprocess.run(['ssh-add', ssh_key_path], check=True)
                else:
                    subprocess.run(['ssh-add', ssh_key_path], check=True)

            with open(os.path.expanduser('~/.ssh/config'), 'w') as ssh_config_file:
                ssh_config_file.write(f"""
Host github.com
    HostName github.com
    User git
    IdentityFile {ssh_key_path}
    IdentitiesOnly yes
""")

            subprocess.run(['git', 'init'], check=True)
            subprocess.run(['git', 'checkout', '-b', CONFIG['github_branch']], check=True)

            remotes = subprocess.check_output(['git', 'remote']).decode('utf-8').strip().split('\n')
            if 'origin' in remotes:
                subprocess.run(['git', 'remote', 'remove', 'origin'], check=True)

            subprocess.run(['git', 'remote', 'add', 'origin', CONFIG['github_repo']], check=True)
        except Exception as e:
            fehler_beenden(f"Fehler bei der Git-Konfiguration: {e}")

# =============================================================================
# 3. GITHUB UPLOAD
# =============================================================================

def upload_to_github():
    """Lädt die generierte Hosts-Datei auf das GitHub-Repository hoch."""
    try:
        if not os.path.exists('hosts'):
            log("Die Hosts-Datei fehlt. Upload wird übersprungen.", logging.WARNING)
            return

        subprocess.run(['git', 'add', 'hosts'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Automatische Aktualisierung der Hosts-Datei'], check=True)
        subprocess.run(['git', 'push', 'origin', CONFIG['github_branch']], check=True)
        log("Hosts-Datei erfolgreich auf GitHub hochgeladen.", logging.INFO)
    except subprocess.CalledProcessError as e:
        log(f"Fehler beim Hochladen der Hosts-Datei: {e}", logging.ERROR)

# =============================================================================
# 4. HILFSFUNKTIONEN FÜR SYSTEMINFORMATIONEN
# =============================================================================

def get_cpu_load():
    """Liest die CPU-Last aus /proc/loadavg."""
    try:
        with open('/proc/loadavg', 'r') as f:
            loadavg = f.read().strip().split()
        cpu_load_1_min = float(loadavg[0])  # 1-Minuten-Load Average
        return cpu_load_1_min
    except Exception as e:
        log(f"Fehler beim Lesen von /proc/loadavg: {e}", logging.ERROR)
        return 0.0

def get_free_memory():
    """Ermittelt den verfügbaren Speicher in Bytes aus /proc/meminfo."""
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.readlines()
        mem_available = next((line for line in meminfo if "MemAvailable" in line), None)
        if mem_available:
            free_memory_kb = int(mem_available.split()[1])  # Wert in kB
            return free_memory_kb * 1024  # Umrechnung in Bytes
    except Exception as e:
        log(f"Fehler beim Lesen von /proc/meminfo: {e}", logging.ERROR)
        return 0

def berechne_md5(text):
    """Berechnet den MD5-Hash des gegebenen Textes."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def lade_domain_md5():
    """Lädt die domain_md5.json Datei."""
    try:
        with open(os.path.join(skript_verzeichnis, 'tmp', 'domain_md5.json')) as json_datei:
            return json.load(json_datei)
    except FileNotFoundError:
        return {}

def speichere_domain_md5(domain_md5):
    """Speichert die domain_md5.json Datei."""
    with open(os.path.join(skript_verzeichnis, 'tmp', 'domain_md5.json'), 'w') as json_datei:
        json.dump(domain_md5, json_datei, indent=4)

def speichere_liste_temporär(url, domains):
    """Speichert getestete Domains einer Liste temporär ab."""
    try:
        temp_path = os.path.join(skript_verzeichnis, 'tmp', f"{url.replace('://', '_').replace('/', '_')}.tmp")
        with open(temp_path, 'w') as temp_file:
            for domain in domains:
                temp_file.write(f"{domain}\n")
        log(f"Liste {url} wurde temporär gespeichert.")
    except Exception as e:
        log(f"Fehler beim Speichern der temporären Liste {url}: {e}", logging.ERROR)

def calculate_batch_size():
    """Berechnet die dynamische Batch-Größe basierend auf verfügbarem Speicher und Systemgrenzen."""
    free_memory = get_free_memory()
    estimated_domains_per_batch = free_memory // 1024 // 70  # Schätzung: 70 Bytes pro Domain
    max_batch_size = CONFIG.get("batch_größe", 100)
    
    # Prüfen, ob die berechnete Größe sinnvoll ist
    batch_size = max(1, min(max_batch_size, estimated_domains_per_batch))
    if batch_size < max_batch_size:
        log(f"Warnung: Batch-Größe reduziert auf {batch_size} basierend auf verfügbaren Ressourcen.", logging.WARNING)
        log(f"Grund: Verfügbarer Speicher: {free_memory / (1024 * 1024):.2f} MB", logging.WARNING)
    
    # Ausgabe der Werte und Einschätzung
    log(f"Berechneter verfügbarer Speicher: {free_memory / (1024 * 1024):.2f} MB", logging.DEBUG)
    log(f"Geschätzte Domains pro Batch: {estimated_domains_per_batch}", logging.DEBUG)
    log(f"Empfohlene Batch-Größe: {batch_size} (Maximal erlaubt: {max_batch_size})", logging.DEBUG)
    if batch_size < max_batch_size:
        log("Hinweis: Es könnte mehr Batch-Größe möglich sein, wenn die Ressourcenkonfiguration angepasst wird.", logging.DEBUG)

    return batch_size

def calculate_dynamic_resources(domain_count, max_jobs=None):
    """Berechnet dynamisch die parallelen Jobs und gibt Empfehlungen basierend auf aktuellen Ressourcen."""
    max_jobs = max_jobs or CONFIG.get('max_parallel_jobs', 10)

    # Dynamische Ressourcenberechnung
    cpu_load = get_cpu_load()
    cpu_cores = os.cpu_count() or 1
    free_memory = get_free_memory()

    # Berechnung der maximal möglichen parallelen Jobs
    max_jobs_by_cpu = max(1, int(cpu_cores / (cpu_load + 1)))
    max_jobs_by_memory = max(1, int((free_memory * 0.75) / (domain_count * 70)))  # 70 Bytes pro Domain
    max_parallel_jobs = min(max_jobs_by_cpu, max_jobs_by_memory, max_jobs)

    # Ausgabe der Werte und Einschätzung
    log(f"Aktuelle CPU-Auslastung: {cpu_load:.2f}, verfügbare CPU-Kerne: {cpu_cores}", logging.DEBUG)
    log(f"Verfügbarer Speicher: {free_memory / (1024 * 1024):.2f} MB")
    log(f"Berechnete parallele Jobs basierend auf CPU: {max_jobs_by_cpu}", logging.DEBUG)
    log(f"Berechnete parallele Jobs basierend auf Speicher: {max_jobs_by_memory}", logging.DEBUG)
    log(f"Empfohlene parallele Jobs: {max_parallel_jobs} (Maximal erlaubt: {max_jobs})", logging.DEBUG)

    # Warnung ausgeben, wenn die parallelen Jobs reduziert wurden
    if max_parallel_jobs < max_jobs:
        log(f"Warnung: Parallele Jobs reduziert auf {max_parallel_jobs} basierend auf aktuellen Ressourcen.", logging.DEBUG)
        log("Hinweis: Es könnten mehr parallele Jobs möglich sein, wenn die Ressourcenkonfiguration angepasst wird.", logging.DEBUG)

    return max_parallel_jobs

def erstelle_dnsmasq_conf(domains):
    """Erstellt die dnsmasq Konfigurationsdatei und startet dnsmasq nur bei Änderungen oder wenn die aktuelle Datei leer ist."""
    temp_conf_path = os.path.join(skript_verzeichnis, 'tmp', 'temp_adblock.conf')
    with open(temp_conf_path, 'w') as conf_file:
        for domain in sortiere_domains(domains):
            conf_file.write(f"address=/{domain}/{CONFIG['web_server_ipv4']}\n")
            conf_file.write(f"address=/{domain}/{CONFIG['web_server_ipv6']}\n")

    # Prüfen, ob die aktuelle Konfiguration existiert und leer ist
    if not os.path.exists(CONFIG['dns_konfiguration']) or os.stat(CONFIG['dns_konfiguration']).st_size == 0:
        log("Aktuelle dnsmasq-Konfiguration fehlt oder ist leer. Erstelle neu und starte dnsmasq.")
        os.replace(temp_conf_path, CONFIG['dns_konfiguration'])
        subprocess.run(['systemctl', 'restart', 'dnsmasq'])
        return

    # Prüfen, ob sich die neue Konfiguration von der bestehenden unterscheidet
    if not filecmp.cmp(temp_conf_path, CONFIG['dns_konfiguration']):
        log("dnsmasq-Konfiguration hat sich geändert. Erstelle neu und starte dnsmasq.")
        os.replace(temp_conf_path, CONFIG['dns_konfiguration'])
        subprocess.run(['systemctl', 'restart', 'dnsmasq'])
    else:
        log("Keine Änderungen in der dnsmasq-Konfiguration. Neustart wird übersprungen.")
        os.remove(temp_conf_path)

def sortiere_domains(domains):
    """Sortiert die Domains numerisch und alphabetisch."""
    return sorted(domains, key=lambda x: (x.split('.')[-1], x))

def erstelle_hosts_datei(domains):
    """Erstellt die Hosts-Datei."""
    log("Beginne mit der Erstellung der hosts.txt Datei")
    hosts_datei_pfad = os.path.join(skript_verzeichnis, 'hosts.txt')
    with open(hosts_datei_pfad, 'w') as hosts_file:
        for domain in sortiere_domains(domains):
            hosts_file.write(f"0.0.0.0 {domain}\n")
    log("Hosts-Datei erstellt")

# =============================================================================
# 5. FORTSCHRITTS- UND KONFIGURATIONSMANAGEMENT
# =============================================================================

def speichere_fortschritt(daten, dateipfad="fortschritt.json"):
    """Speichert den Fortschritt in einer JSON-Datei."""
    try:
        with open(os.path.join(skript_verzeichnis, dateipfad), 'w') as file:
            json.dump(daten, file, indent=4)
        log(f"Fortschrittsdaten gespeichert in {dateipfad}.", logging.INFO)
    except Exception as e:
        log(f"Fehler beim Speichern der Fortschrittsdaten: {e}", logging.ERROR)

def lade_fortschritt(dateipfad="fortschritt.json"):
    """Lädt den gespeicherten Fortschritt aus einer JSON-Datei."""
    try:
        with open(os.path.join(skript_verzeichnis, dateipfad), 'r') as file:
            daten = json.load(file)
        log(f"Fortschrittsdaten geladen aus {dateipfad}.", logging.INFO)
        return daten
    except FileNotFoundError:
        log("Keine Fortschrittsdaten gefunden. Beginne neu.", logging.INFO)
        return {}
    except Exception as e:
        log(f"Fehler beim Laden der Fortschrittsdaten: {e}", logging.ERROR)
        return {}

def lade_konfiguration(dateipfad):
    """Lädt und validiert die Konfiguration mit JSON-Validierung."""
    try:
        with open(dateipfad, 'r') as file:
            config = json.load(file)

        # Validierung der Konfigurationswerte
        if config.get("max_parallel_jobs") < 1:
            raise ValueError("max_parallel_jobs muss mindestens 1 sein.")
        if config.get("batch_größe") < 1:
            raise ValueError("batch_größe muss mindestens 1 sein.")
        
        return config
    except json.JSONDecodeError as e:
        fehler_beenden(f"Fehler beim Laden der Konfiguration: {e}")
    except KeyError as e:
        fehler_beenden(f"Konfigurationsfehler: {e}")

# =============================================================================
# 6. LOGGING UND FEHLERBEHANDLUNG
# =============================================================================

def konfiguriere_logging(log_datei):
    """Konfiguriert das Logging mit der in der config.json angegebenen Ebene."""
    level = CONFIG.get('logging_level', 'INFO').upper()
    numeric_level = getattr(logging, level, logging.INFO)

    if CONFIG.get("detailed_log", False):
        numeric_level = logging.DEBUG  # Überschreibt Logging-Level bei detaillierten Logs

    logging.basicConfig(
        level=numeric_level,  # Setze den globalen Log-Level
        format=LOG_FORMAT,
        filename=log_datei,  # Schreibe direkt in die Datei
        filemode='w'  # Überschreibe die Datei bei jedem Start
    )
    log(f"Logging-Level auf {level} gesetzt.", logging.INFO)

def log(nachricht, level=logging.INFO):
    """Schreibt eine Nachricht in die Log-Datei."""
    logger = logging.getLogger()
    if level >= logger.getEffectiveLevel():  # Nur loggen, wenn der Level >= globalem Log-Level ist
        logger.log(level, nachricht)

def fehler_beenden(nachricht):
    """Beendet das Skript bei einem Fehler und aktualisiert die Statistik."""
    log(nachricht, logging.ERROR)
    STATISTIK["durchlauf_fehlgeschlagen"] = True
    STATISTIK["fehlermeldung"] = nachricht
    sende_email("Fehler im AdBlock-Skript", erstelle_email_text())
    exit(1)

# =============================================================================
# 7. DATEI- UND VERZEICHNISMANAGEMENT
# =============================================================================

def erstelle_standard_datei(dateipfad, inhalt=None, leer=False):
    """Erstellt eine Datei mit Standardwerten oder leerem Inhalt, wenn sie nicht existiert."""
    if not os.path.exists(dateipfad):
        with open(dateipfad, 'w') as datei:
            if leer:
                datei.write("")  # Leeren Inhalt schreiben
            else:
                if isinstance(inhalt, str):
                    datei.write(inhalt)
                else:
                    json.dump(inhalt, datei, indent=4)

def initialisiere_verzeichnisse_und_dateien():
    """Überprüft und erstellt notwendige Verzeichnisse und Dateien."""
    os.makedirs(os.path.join(skript_verzeichnis, 'tmp'), exist_ok=True)
    erstelle_standard_datei(os.path.join(skript_verzeichnis, 'config.json'), STANDARD_CONFIG)
    erstelle_standard_datei(os.path.join(skript_verzeichnis, 'tmp', 'statistik.json'), STATISTIK)
    erstelle_standard_datei(os.path.join(skript_verzeichnis, 'hosts_sources.conf'), STANDARD_HOSTS_SOURCES)
    erstelle_standard_datei(os.path.join(skript_verzeichnis, 'tmp', 'domain_md5.json'), {})
    erstelle_standard_datei(os.path.join(skript_verzeichnis, 'whitelist.txt'), leer=True)
    erstelle_standard_datei(os.path.join(skript_verzeichnis, 'blacklist.txt'), leer=True)

def bereinige_obsolete_dateien():
    """Bereinigt veraltete oder ungenutzte temporäre Dateien im tmp-Verzeichnis."""
    temp_verzeichnis = os.path.join(skript_verzeichnis, 'tmp')
    aktuelle_urls = set(lade_domain_md5().keys())

    for datei in os.listdir(temp_verzeichnis):
        dateipfad = os.path.join(temp_verzeichnis, datei)
        if not datei.endswith(".tmp"):
            continue

        zugehoerige_url = datei.replace("_", "://").replace(".tmp", "")
        if zugehoerige_url not in aktuelle_urls:
            try:
                os.remove(dateipfad)
                log(f"Obsolete Datei gelöscht: {dateipfad}", logging.INFO)
            except Exception as e:
                log(f"Fehler beim Löschen der Datei {dateipfad}: {e}", logging.ERROR)

def aktualisiere_hosts_sources():
    """Aktualisiert die Liste der Hosts-Quellen basierend auf Änderungen."""
    with open(os.path.join(skript_verzeichnis, 'hosts_sources.conf')) as f:
        aktuelle_urls = {line.strip() for line in f if line.strip() and not line.startswith('#')}

    gespeicherte_urls = set(lade_domain_md5().keys())
    neue_urls = aktuelle_urls - gespeicherte_urls
    entfernte_urls = gespeicherte_urls - aktuelle_urls

    # Neue URLs initialisieren
    for url in neue_urls:
        log(f"Neue URL gefunden: {url}. Initialisierung...")
        extrahiere_domains_aus_liste(url)

    # Entfernte URLs bereinigen
    for url in entfernte_urls:
        log(f"URL entfernt: {url}. Bereinige zugehörige Daten...")
        domain_md5 = lade_domain_md5()
        if url in domain_md5:
            del domain_md5[url]
        speichere_domain_md5(domain_md5)

# =============================================================================
# 8. DNS UND DOMAIN-VALIDIERUNG
# =============================================================================

def ist_gueltige_domain(domain):
    """Überprüft, ob eine Domain gültig ist."""
    domain_regex = re.compile(
        r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})+$"
    )
    return bool(domain_regex.match(domain))

def test_dns_entry(domain, record_type='A'):
    """Testet einen spezifischen DNS-Eintragstyp für eine Domain mit Wiederholungslogik."""
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = CONFIG['dns_server_list']
        retries = CONFIG.get("max_retries", 3)
        for versuch in range(retries):
            try:
                resolver.resolve(domain, record_type, lifetime=CONFIG.get('domain_timeout', 5))
                return True
            except (dns.resolver.Timeout, dns.resolver.NXDOMAIN) as e:
                log(f"DNS-Fehler bei {domain} ({record_type}, Versuch {versuch+1}/{retries}): {e}", logging.DEBUG)
                if versuch == retries - 1:
                    return False
                time.sleep(CONFIG.get("retry_delay", 2))
    except Exception as e:
        log(f"Allgemeiner Fehler beim Testen von {domain} ({record_type}): {e}", logging.DEBUG)
        return False

# =============================================================================
# 9. BATCH-VERARBEITUNG UND DOMAIN-EXTRAKTION
# =============================================================================

def messen(func):
    """Dekorator zum Messen der Laufzeit einer Funktion."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Die Funktion '{func.__name__}' dauerte {end_time - start_time:.2f} Sekunden.")
        return result
    return wrapper

@messen
def teste_domains_batch(domains):
    """Testet eine Liste von Domains in einem Batch mit dynamisch berechneten Ressourcen."""
    results = {}
    resolver_index = random.randint(0, len(CONFIG['dns_server_list']) - 1)
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [CONFIG['dns_server_list'][resolver_index]]

    batch_index = 0
    total_domains = len(domains)

    while batch_index < total_domains:
        batch_size = calculate_batch_size()
        max_jobs = calculate_dynamic_resources(total_domains)
        current_batch = domains[batch_index:batch_index + batch_size]
        
        log(f"Starte Batch {batch_index // batch_size + 1} mit Größe {batch_size} und {max_jobs} parallelen Jobs.", logging.INFO)

        with ThreadPoolExecutor(max_workers=max_jobs) as executor:
            futures = {executor.submit(test_single_or_batch, domain, resolver_index): domain for domain in current_batch}

            for future in concurrent.futures.as_completed(futures):
                domain = futures[future]
                try:
                    reachable = future.result()
                    results[domain] = reachable
                    with dns_cache_lock:
                        DNS_CACHE[domain] = reachable
                    if not reachable and CONFIG.get("speichere_nicht_erreichbare", False):
                        speichere_nicht_erreichbare_domains(domain, os.path.join(skript_verzeichnis, 'nicht_erreichbare.txt'))
                except Exception as e:
                    log(f"Fehler beim Testen der Domain {domain}: {e}", logging.DEBUG)
                    results[domain] = False

        batch_index += batch_size
        log(f"Batch abgeschlossen: {batch_index} von {total_domains} Domains verarbeitet.", logging.INFO)

    return results

def test_single_or_batch(domain, resolver_index):
    """Führt einen Domain-Test aus und fällt bei Fehlern auf einen anderen Resolver zurück."""
    try:
        return test_dns_entry(domain, 'A')
    except Exception as e:
        log(f"Fehler beim Testen der Domain {domain}: {e}. Wechsel auf anderen Resolver.", logging.WARNING)
        new_resolver_index = (resolver_index + 1) % len(CONFIG['dns_server_list'])
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [CONFIG['dns_server_list'][new_resolver_index]]
            return test_dns_entry(domain, 'A')
        except Exception as second_error:
            log(f"Zweiter Fehler beim Testen von {domain} mit anderem Resolver: {second_error}", logging.ERROR)
            return False

def extrahiere_domains_aus_liste(url):
    """Extrahiert Domains aus einer Hosts-Datei und ordnet sie der jeweiligen Liste zu."""
    try:
        log(f"Beginne Extrahieren der Domains von {url}")
        domain_md5 = lade_domain_md5()

        # Prüfe, ob die Liste geändert wurde
        if url in domain_md5:
            saved_md5 = domain_md5[url]['md5']
            log(f"Prüfe, ob sich die Liste {url} geändert hat...")
            retries = CONFIG.get("max_retries", 3)
            for versuch in range(retries):
                try:
                    # Nutze If-None-Match, wenn der Server ETags unterstützt
                    response = requests.get(url, headers={"If-None-Match": saved_md5}, timeout=10)
                    if response.status_code == 304:  # Liste ist unverändert
                        log(f"Keine Änderungen in {url}, überspringe Verarbeitung.")
                        return url, domain_md5[url]['domains'], saved_md5
                    break
                except requests.exceptions.RequestException as e:
                    log(f"Fehler bei Anfrage {url} (Versuch {versuch+1}/{retries}): {e}", logging.WARNING)
                    if versuch == retries - 1:
                        raise
                    time.sleep(CONFIG.get("retry_delay", 5))
        else:
            log(f"Keine gespeicherte MD5-Prüfsumme für {url}. Starte Download.")

        # Liste herunterladen
        retries = CONFIG.get("max_retries", 3)
        for versuch in range(retries):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                log(f"Fehler bei Anfrage {url} (Versuch {versuch+1}/{retries}): {e}", logging.WARNING)
                if versuch == retries - 1:
                    raise
                time.sleep(CONFIG.get("retry_delay", 5))

        content = response.text
        current_md5 = berechne_md5(content)

        # Prüfen, ob sich die Liste geändert hat
        if url in domain_md5 and domain_md5[url]['md5'] == current_md5:
            log(f"Keine Änderungen in {url}, überspringe Verarbeitung.")
            return url, domain_md5[url]['domains'], current_md5

        # Domains extrahieren
        lines = content.splitlines()
        domains = set()
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            teile = line.split()
            if len(teile) > 1 and re.match(r"^\d{1,3}(\.\d{1,3}){3}$", teile[0]):
                domain = teile[1].strip()
                domain = re.sub(r'^www\.', '', domain)
                if ist_gueltige_domain(domain):
                    domains.add(domain)

        # Aktualisiere die gespeicherte MD5-Prüfsumme und die Domains
        domain_md5[url] = {"md5": current_md5, "domains": list(domains)}
        speichere_domain_md5(domain_md5)
        speichere_liste_temporär(url, domains)

        log(f"Extrahierte {len(domains)} Domains aus {url}")
        return url, domains, current_md5

    except Exception as e:
        log(f"Fehler beim Extrahieren der Domains von {url}: {e}", logging.ERROR)
        STATISTIK["fehlerhafte_lists"] += 1
        return url, set(), None

# =============================================================================
# 1. DATENVERARBEITUNG UND DUPLIKATMANAGEMENT
# =============================================================================

def entferne_duplikate_mit_prioritaet(domains_dict):
    """Entfernt Duplikate aus den Listen, wobei Domains aus höher priorisierten Listen bevorzugt werden."""
    priorisierte_domains = set()
    bearbeitete_domains_dict = {}

    for url, data in domains_dict.items():
        domains = data["domains"]
        unique_domains = []
        for domain in domains:
            if domain not in priorisierte_domains:
                unique_domains.append(domain)
                priorisierte_domains.add(domain)
        bearbeitete_domains_dict[url] = {"domains": unique_domains, "md5": data["md5"]}
        STATISTIK["duplikate_pro_liste"][url] = len(domains) - len(unique_domains)

    return bearbeitete_domains_dict

def pruefe_und_entferne_leere_listen(domains_dict):
    """Prüft und markiert leere Listen zur Entfernung."""
    leere_listen = []
    for url, data in domains_dict.items():
        if not data["domains"]:
            leere_listen.append(url)

    for url in leere_listen:
        log(f"Liste {url} ist leer und wird zur Entfernung empfohlen.", logging.WARNING)
        del domains_dict[url]

    return domains_dict

# =============================================================================
# 11. FORTSCHRITTSSPEICHERUNG
# =============================================================================

def speichere_fortschritt(daten, dateipfad="fortschritt.json"):
    """Speichert den Fortschritt in einer JSON-Datei."""
    try:
        with open(os.path.join(skript_verzeichnis, dateipfad), 'w') as file:
            json.dump(daten, file, indent=4)
        log(f"Fortschrittsdaten gespeichert in {dateipfad}.", logging.INFO)
    except Exception as e:
        log(f"Fehler beim Speichern der Fortschrittsdaten: {e}", logging.ERROR)

def lade_fortschritt(dateipfad="fortschritt.json"):
    """Lädt den gespeicherten Fortschritt aus einer JSON-Datei."""
    try:
        with open(os.path.join(skript_verzeichnis, dateipfad), 'r') as file:
            daten = json.load(file)
        log(f"Fortschrittsdaten geladen aus {dateipfad}.", logging.INFO)
        return daten
    except FileNotFoundError:
        log("Keine Fortschrittsdaten gefunden. Beginne neu.", logging.INFO)
        return {}
    except Exception as e:
        log(f"Fehler beim Laden der Fortschrittsdaten: {e}", logging.ERROR)
        return {}

# =============================================================================
# 12. BEWERTUNGS- UND STATISTIKFUNKTIONEN
# =============================================================================

def bewerte_listen():
    """Bewertet die Hosts-Listen basierend auf den gesammelten Statistiken."""
    bewertung = []
    for url in STATISTIK["erreichbare_pro_liste"].keys():
        erreichbar = STATISTIK["erreichbare_pro_liste"].get(url, 0)
        nicht_erreichbar = STATISTIK["nicht_erreichbare_pro_liste"].get(url, 0)
        duplikate = STATISTIK["duplikate_pro_liste"].get(url, 0)
        gesamt = erreichbar + nicht_erreichbar
        effizient = erreichbar / gesamt if gesamt > 0 else 0
        wert = erreichbar - (duplikate + nicht_erreichbar)
        bewertung.append((url, gesamt, erreichbar, nicht_erreichbar, duplikate, effizient, wert))

    bewertung.sort(key=lambda x: x[-1], reverse=True)

    # Entferne ineffiziente Listen
    for item in bewertung:
        if item[1] == 0 or item[-1] < 0:
            log(f"Liste {item[0]} wird entfernt, da sie ineffizient ist.")
            del STATISTIK["erreichbare_pro_liste"][item[0]]

    STATISTIK["list_bewertung"] = bewertung
    return bewertung

def speichere_bewertung():
    """Speichert die Bewertung der Hosts-Listen in einer Datei."""
    bewertung_datei = os.path.join(skript_verzeichnis, 'bewertung.json')
    with open(bewertung_datei, 'w') as datei:
        json.dump(STATISTIK["list_bewertung"], datei, indent=4)
    log(f"Bewertung der Listen in {bewertung_datei} gespeichert.", logging.INFO)

# =============================================================================
# 13. STATISTIKAKTUALISIERUNG UND EMAIL
# =============================================================================

def aktualisiere_gesamtstatistik():
    """Aktualisiert die Gesamtstatistik mit den aktuellen Laufdaten."""
    laufstatistik = {
        "getestete_domains": STATISTIK["getestete_domains"],
        "erreichbare_domains": STATISTIK["erreichbare_domains"],
        "nicht_erreichbare_domains": STATISTIK["nicht_erreichbare_domains"],
        "fehlerhafte_lists": STATISTIK["fehlerhafte_lists"],
        "duplikate": STATISTIK["duplikate"],
        "durchlauf_fehlgeschlagen": STATISTIK["durchlauf_fehlgeschlagen"]
    }
    STATISTIK["gesamtstatistik"].append(laufstatistik)

def erstelle_email_text():
    """Erstellt den Text der E-Mail-Benachrichtigung."""
    status = "Erfolgreich" if not STATISTIK["durchlauf_fehlgeschlagen"] else "Fehlgeschlagen"
    fehlermeldung = STATISTIK["fehlermeldung"] if STATISTIK["durchlauf_fehlgeschlagen"] else "Keine"

    email_text = f"Der aktuelle Durchlauf des AdBlock-Skripts ist {status}.\n\n"
    
    if STATISTIK["durchlauf_fehlgeschlagen"]:
        email_text += f"Fehlermeldung: {fehlermeldung}\n\n"

    # Gesamtstatistik aller Läufe
    email_text += "Gesamtstatistik:\n"
    email_text += "----------------\n"
    gesamt_statistik = {
        "getestete_domains": sum(lauf['getestete_domains'] for lauf in STATISTIK["gesamtstatistik"]),
        "erreichbare_domains": sum(lauf['erreichbare_domains'] for lauf in STATISTIK["gesamtstatistik"]),
        "nicht_erreichbare_domains": sum(lauf['nicht_erreichbare_domains'] for lauf in STATISTIK["gesamtstatistik"]),
        "fehlerhafte_lists": sum(lauf['fehlerhafte_lists'] for lauf in STATISTIK["gesamtstatistik"]),
        "duplikate": sum(lauf['duplikate'] for lauf in STATISTIK["gesamtstatistik"]),
    }
    for key, value in gesamt_statistik.items():
        email_text += f"{key.replace('_', ' ').capitalize()}: {value}\n"

    # Aktuelle Laufstatistik
    email_text += "\nStatistik des aktuellen Laufs:\n"
    email_text += "-----------------------------\n"
    aktuelle_statistik = {
        "getestete_domains": STATISTIK["getestete_domains"],
        "erreichbare_domains": STATISTIK["erreichbare_domains"],
        "nicht_erreichbare_domains": STATISTIK["nicht_erreichbare_domains"],
        "fehlerhafte_lists": STATISTIK["fehlerhafte_lists"],
        "gesamtanzahl_domains_in_den_listen": STATISTIK["gesamt_domains"],
        "duplikate": STATISTIK["duplikate"],
    }
    for key, value in aktuelle_statistik.items():
        email_text += f"{key.replace('_', ' ').capitalize()}: {value}\n"

    email_text += "\nErgebnisse pro Liste:\n"
    email_text += "---------------------\n"
    for url, gesamt, erreichbar, nicht_erreichbar, duplikate, wert in STATISTIK["list_bewertung"]:
        email_text += f"Liste: {url}\n"
        email_text += f"    Gesamt: {gesamt}\n"
        email_text += f"    Erreichbar: {erreichbar}\n"
        email_text += f"    Nicht erreichbar: {nicht_erreichbar}\n"
        email_text += f"    Duplikate: {duplikate}\n"
        email_text += f"    Bewertung: {wert}\n\n"

    return email_text

def sende_email(betreff, text, fehler=False):
    """Sendet eine E-Mail mit dem gegebenen Betreff und Text."""
    if CONFIG.get('send_email', False):
        try:
            EMAIL = CONFIG['email']
            ABSENDER = CONFIG['email_absender']
            nachricht = f"Subject: {betreff}\nFrom: {ABSENDER}\nTo: {EMAIL}\n\n{text}"
            p = subprocess.Popen(["/usr/sbin/sendmail", "-t"], stdin=subprocess.PIPE)
            p.communicate(nachricht.encode())
            log(f"E-Mail gesendet an {EMAIL}: {betreff}")
        except Exception as e:
            log(f"Fehler beim Senden der E-Mail: {e}", logging.ERROR)

# =============================================================================
# 14. HAUPTPROZESS
# =============================================================================

def hauptprozess():
    """Hauptprozess des Skripts."""
    try:
        # Initialisieren
        initialisiere_verzeichnisse_und_dateien()
        global CONFIG
        CONFIG = lade_konfiguration(os.path.join(skript_verzeichnis, 'config.json'))
        konfiguriere_logging(CONFIG['log_datei'])

        log("Starte den Hauptprozess...", logging.INFO)

        if CONFIG['github_upload']:
            setup_git()

        # Hosts-Quellen aktualisieren
        aktualisiere_hosts_sources()
        with open(os.path.join(skript_verzeichnis, 'hosts_sources.conf')) as file:
            urls = [line.strip() for line in file if line.strip() and not line.startswith("#")]

        domains_dict = {}

        # Domains aus den URLs extrahieren
        with ThreadPoolExecutor(max_workers=CONFIG.get('max_parallel_jobs', 10)) as executor:
            futures = {executor.submit(extrahiere_domains_aus_liste, url): url for url in urls}
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    _, domains, _ = future.result()
                    domains_dict[url] = {"domains": domains, "md5": lade_domain_md5().get(url, {}).get("md5")}
                except Exception as e:
                    log(f"Fehler beim Extrahieren der Domains von {url}: {e}", logging.ERROR)

        # Duplikate mit Priorität entfernen
        domains_dict = entferne_duplikate_mit_prioritaet(domains_dict)

        # Leere Listen entfernen
        domains_dict = pruefe_und_entferne_leere_listen(domains_dict)

        # Alle Domains sammeln
        alle_domains = set(domain for data in domains_dict.values() for domain in data["domains"])
        log(f"Extrahiert: {len(alle_domains)} Domains aus den Quellen.")

        # Whitelist und Blacklist anwenden
        with open(os.path.join(skript_verzeichnis, 'whitelist.txt')) as whitelist_file:
            whitelist = {line.strip() for line in whitelist_file if line.strip()}
        with open(os.path.join(skript_verzeichnis, 'blacklist.txt')) as blacklist_file:
            blacklist = {line.strip() for line in blacklist_file if line.strip()}

        alle_domains.difference_update(whitelist)
        alle_domains.update(blacklist)
        log(f"Domains nach Whitelist und Blacklist gefiltert: {len(alle_domains)} verbleibend.")

        # Domains testen
        erreichbare_domains = set()
        nicht_erreichbare_domains = set()
        batch_size = calculate_batch_size()
        batches = [list(alle_domains)[i:i + batch_size] for i in range(0, len(alle_domains), batch_size)]

        for batch_index, batch in enumerate(batches, start=1):
            log(f"Starte Batch {batch_index}/{len(batches)}.", logging.INFO)
            batch_results = teste_domains_batch(batch)

            for domain, erreichbar in batch_results.items():
                STATISTIK["getestete_domains"] += 1
                if erreichbar:
                    erreichbare_domains.add(domain)
                    STATISTIK["erreichbare_domains"] += 1
                else:
                    nicht_erreichbare_domains.add(domain)
                    STATISTIK["nicht_erreichbare_domains"] += 1

        log(f"Test abgeschlossen: {len(erreichbare_domains)} erreichbare Domains, {len(nicht_erreichbare_domains)} nicht erreichbar.")

        # Ergebnisse speichern
        speichere_domain_md5(lade_domain_md5())
        erstelle_dnsmasq_conf(erreichbare_domains)
        erstelle_hosts_datei(erreichbare_domains)

        # Upload zu GitHub
        if CONFIG['github_upload']:
            upload_to_github()

        # Listen bewerten und speichern
        bewerte_listen()
        speichere_bewertung()

        log("Hauptprozess erfolgreich abgeschlossen.", logging.INFO)

    except Exception as e:
        fehler_beenden(f"Unerwarteter Fehler im Hauptprozess: {e}")

    finally:
        sende_email("AdBlock Skript abgeschlossen", erstelle_email_text())

# =============================================================================
# 15. EINSTIEGSPUNKT
# =============================================================================

if __name__ == "__main__":
    try:
        # Hauptprozess starten
        hauptprozess()
    except Exception as e:
        fehler_beenden(f"Unerwarteter Fehler: {str(e)}")
