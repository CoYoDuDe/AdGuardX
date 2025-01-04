def lade_whitelist():
    with open("whitelist.txt", "r") as file:
        return {line.strip() for line in file if line.strip()}

def lade_blacklist():
    with open("blacklist.txt", "r") as file:
        return {line.strip() for line in file if line.strip()}
