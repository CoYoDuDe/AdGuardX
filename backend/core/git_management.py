import os
import subprocess
import json
from logging import getLogger

logger = getLogger(__name__)

def setup_git(config):
    """Initialisiert Git-Repository und konfiguriert SSH-Zugang."""
    repo_path = os.getcwd()
    if not os.path.exists(os.path.join(repo_path, ".git")):
        logger.info("Git-Repository wird initialisiert...")
        subprocess.run(["git", "init"], check=True)

    user_name = config.get("git_user", "DefaultUser")
    user_email = config.get("git_email", "default@example.com")

    subprocess.run(["git", "config", "user.name", user_name], check=True)
    subprocess.run(["git", "config", "user.email", user_email], check=True)

    ssh_key_path = os.path.expanduser("~/.ssh/adblock_rsa")
    if not os.path.exists(ssh_key_path):
        logger.info("SSH-Key wird erstellt...")
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-b", "4096", "-C", user_email, "-f", ssh_key_path, "-N", ""],
            check=True,
        )

    subprocess.run(["git", "remote", "add", "origin", config["github_repo"]], check=True)

def upload_to_github(branch="main"):
    """Lädt Änderungen ins GitHub-Repository hoch."""
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Automatische Aktualisierung"], check=True)
        subprocess.run(["git", "push", "-u", "origin", branch], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Fehler beim Hochladen: {e}")
