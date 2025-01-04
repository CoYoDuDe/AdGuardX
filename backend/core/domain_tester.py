import dns.resolver
from threading import Lock

dns_cache = {}
dns_cache_lock = Lock()

def test_domain(domain, record_type='A'):
    global dns_cache
    with dns_cache_lock:
        if domain in dns_cache:
            return dns_cache[domain]

    resolver = dns.resolver.Resolver()
    try:
        resolver.resolve(domain, record_type)
        with dns_cache_lock:
            dns_cache[domain] = True
        return True
    except Exception:
        with dns_cache_lock:
            dns_cache[domain] = False
        return False
