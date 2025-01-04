from multiprocessing import Pool
from adguardx.utils.dns_utils import test_dns_entry

def teste_domains_parallel(domains, workers=4):
    """Testet eine Liste von Domains parallel."""
    with Pool(workers) as pool:
        results = pool.map(test_dns_entry, domains)
    return results
