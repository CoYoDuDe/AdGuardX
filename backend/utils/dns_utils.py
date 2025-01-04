import dns.resolver
import os

def test_dns_entry(domain):
    resolver = dns.resolver.Resolver()
    try:
        resolver.resolve(domain, "A")
        return True
    except:
        return False

def teste_domains_batch(domains):
    results = {}
    for domain in domains:
        results[domain] = test_dns_entry(domain)
    return results

def erstelle_dnsmasq_conf(domains):
    conf_path = "dnsmasq.conf"
    with open(conf_path, "w") as file:
        for domain in domains:
            file.write(f"address=/{domain}/127.0.0.1\n")
    os.system("systemctl restart dnsmasq")
