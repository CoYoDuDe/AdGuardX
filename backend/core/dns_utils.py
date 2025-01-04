import dns.resolver
from threading import Lock

class DNSUtils:
    def __init__(self, dns_servers=None):
        self.dns_servers = dns_servers or [
            "8.8.8.8",
            "8.8.4.4",
            "1.1.1.1",
            "1.0.0.1",
        ]
        self.dns_cache = {}
        self.dns_cache_lock = Lock()

    def test_dns_entry(self, domain, record_type="A"):
        """
        Testet einen spezifischen DNS-Eintragstyp für eine Domain.
        :param domain: Die zu testende Domain.
        :param record_type: Der DNS-Eintragstyp (z. B. 'A', 'AAAA').
        :return: True, wenn der DNS-Eintrag auflösbar ist, False sonst.
        """
        with self.dns_cache_lock:
            if domain in self.dns_cache:
                return self.dns_cache[domain]

        resolver = dns.resolver.Resolver()
        resolver.nameservers = self.dns_servers

        try:
            resolver.resolve(domain, record_type, lifetime=5)
            with self.dns_cache_lock:
                self.dns_cache[domain] = True
            return True
        except dns.resolver.NXDOMAIN:
            return False
        except dns.exception.DNSException:
            return False

    def flush_dns_cache(self):
        """
        Leert den DNS-Cache.
        """
        with self.dns_cache_lock:
            self.dns_cache.clear()

    def resolve_domain(self, domain, record_type="A"):
        """
        Löst eine Domain auf und gibt die Ergebnisse zurück.
        :param domain: Die aufzulösende Domain.
        :param record_type: Der DNS-Eintragstyp (z. B. 'A', 'AAAA').
        :return: Eine Liste von Ergebnissen oder eine leere Liste.
        """
        resolver = dns.resolver.Resolver()
        resolver.nameservers = self.dns_servers

        try:
            answer = resolver.resolve(domain, record_type, lifetime=5)
            return [rdata.to_text() for rdata in answer]
        except dns.exception.DNSException:
            return []
