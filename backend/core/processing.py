import concurrent.futures
from dns.resolver import Resolver, NXDOMAIN, Timeout
import re
import random
from collections import defaultdict
from threading import Lock

# Globale Variablen
DNS_CACHE = {}
dns_cache_lock = Lock()

def ist_gueltige_domain(domain):
    """Überprüft, ob eine Domain gültig ist."""
    domain_regex = re.compile(
        r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})+$"
    )
    return bool(domain_regex.match(domain))

def test_dns_entry(domain, dns_servers, timeout=5):
    """Testet einen DNS-Eintrag und prüft, ob die Domain erreichbar ist."""
    global DNS_CACHE, dns_cache_lock

    with dns_cache_lock:
        if domain in DNS_CACHE:
            return DNS_CACHE[domain]

    resolver = Resolver()
    resolver.nameservers = dns_servers
    record_types = ["A", "AAAA"]

    for record in record_types:
        try:
            resolver.resolve(domain, record, lifetime=timeout)
            with dns_cache_lock:
                DNS_CACHE[domain] = True
            return True
        except (NXDOMAIN, Timeout):
            continue
        except Exception as e:
            print(f"Fehler beim DNS-Test für {domain}: {e}")
    
    with dns_cache_lock:
        DNS_CACHE[domain] = False
    return False

def teste_domains_batch(domains, dns_servers, max_parallel=5):
    """Testet eine Liste von Domains in Batches."""
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel) as executor:
        future_to_domain = {executor.submit(test_dns_entry, domain, dns_servers): domain for domain in domains}
        for future in concurrent.futures.as_completed(future_to_domain):
            domain = future_to_domain[future]
            try:
                results[domain] = future.result()
            except Exception as e:
                results[domain] = False
    return results

def entferne_duplikate(domains_dict):
    """Entfernt Duplikate aus mehreren Domain-Listen."""
    unique_domains = set()
    result = defaultdict(list)

    for source, domains in domains_dict.items():
        for domain in domains:
            if domain not in unique_domains:
                unique_domains.add(domain)
                result[source].append(domain)

    return result
