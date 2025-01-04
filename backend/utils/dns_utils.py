import dns.resolver
import re

def ist_gueltige_domain(domain):
    """Prüft, ob eine Domain gültig ist."""
    domain_regex = re.compile(
        r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})+$"
    )
    return bool(domain_regex.match(domain))

def test_dns_entry(domain, record_type='A', dns_servers=None):
    """Testet, ob eine Domain erreichbar ist."""
    resolver = dns.resolver.Resolver()
    resolver.nameservers = dns_servers or ["8.8.8.8", "1.1.1.1"]
    try:
        resolver.resolve(domain, record_type)
        return True
    except dns.exception.DNSException:
        return False
