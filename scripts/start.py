from adguardx.core.dns_processing import teste_domains_parallel
from adguardx.frontend.app import start_http_server

if __name__ == "__main__":
    # Beispiel-Domains testen
    domains = ["example.com", "google.com", "nonexistent-domain.xyz"]
    results = teste_domains_parallel(domains)
    print(results)

    # HTTP-Server starten
    start_http_server()
