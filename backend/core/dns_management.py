import os
import subprocess
import filecmp
from logging import getLogger

logger = getLogger(__name__)

def erstelle_dnsmasq_conf(domains, config):
    """Erstellt und aktualisiert die dnsmasq-Konfiguration."""
    conf_path = config.get("dns_konfiguration", "adblock.conf")
    temp_path = "tmp/temp_dnsmasq.conf"

    with open(temp_path, "w") as file:
        for domain in domains:
            file.write(f"address=/{domain}/{config['web_server_ipv4']}\n")

    if not os.path.exists(conf_path) or not filecmp.cmp(temp_path, conf_path):
        os.replace(temp_path, conf_path)
        subprocess.run(["systemctl", "restart", "dnsmasq"], check=True)
        logger.info("dnsmasq-Konfiguration wurde aktualisiert.")
    else:
        os.remove(temp_path)
        logger.info("Keine Änderungen in der dnsmasq-Konfiguration.")
