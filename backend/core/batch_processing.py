import time
from concurrent.futures import ThreadPoolExecutor
from logging import getLogger

logger = getLogger(__name__)

def teste_domains_batch(domains, test_function, batch_size, max_jobs):
    """Testet Domains in Batches."""
    results = {}
    for i in range(0, len(domains), batch_size):
        batch = domains[i : i + batch_size]
        logger.info(f"Starte Batch {i // batch_size + 1} mit {len(batch)} Domains.")

        with ThreadPoolExecutor(max_workers=max_jobs) as executor:
            futures = {executor.submit(test_function, domain): domain for domain in batch}
            for future in futures:
                domain = futures[future]
                try:
                    results[domain] = future.result()
                except Exception as e:
                    logger.error(f"Fehler bei Domain {domain}: {e}")
    return results
