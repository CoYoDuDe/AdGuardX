#!/usr/bin/env python3


from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import os
import json
import threading
import time
from datetime import datetime
from collections import Counter

# Flask App Setup
app = Flask(__name__)

socketio = SocketIO(app)
batch_progress = {"current": 0, "total": 0}
block_log = []

# Globale Variablen (Simulation von Daten)
lock = threading.Lock()
STATISTIK = {
    "getestete_domains": 1234,
    "erreichbare_domains": 789,
    "nicht_erreichbare_domains": 445,
    "fehlerhafte_lists": 2,
    "duplikate": 56,
    "list_bewertung": [{"url": "https://example.com/hosts1", "effizienz": 0.87}],
}
CONFIG = {
    "github_upload": True,
    "max_parallel_jobs": 10,
    "dns_server_list": ["8.8.8.8", "1.1.1.1"],
}

# Funktionen zur Simulation
def lade_statistik():
    # Simulation: Daten laden
    return STATISTIK

def lade_config():
    # Simulation: Konfiguration laden
    return CONFIG

def speichere_config(neue_config):
    # Simulation: Konfiguration speichern
    with lock:
        CONFIG.update(neue_config)

def starte_domain_tests():
    # Simulation: Domain-Test starten
    with lock:
        STATISTIK["getestete_domains"] += 100
        STATISTIK["erreichbare_domains"] += 80
        STATISTIK["nicht_erreichbare_domains"] += 20

def log_streamer():
    log_file = CONFIG.get('log_datei', '/var/log/adblock.log')
    while True:
        with open(log_file, 'r') as file:
            lines = file.readlines()
        socketio.emit('log_update', {'logs': lines})
        time.sleep(2)

# Routen
@app.route("/")
def dashboard():
    statistik = lade_statistik()
    return render_template("dashboard.html", statistik=statistik)

@app.route("/config", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        neue_config = request.json
        speichere_config(neue_config)
        return jsonify({"status": "success", "message": "Configuration updated!"})
    return render_template("config.html", config=lade_config())

@app.route("/whitelist", methods=["GET", "POST"])
def whitelist():
    if request.method == "POST":
        neue_domain = request.form.get("domain")
        # Simulation: Domain zur Whitelist hinzufügen
        return jsonify({"status": "success", "message": f"{neue_domain} added to whitelist!"})
    return render_template("whitelist.html")

@app.route("/blacklist", methods=["GET", "POST"])
def blacklist():
    if request.method == "POST":
        neue_domain = request.form.get("domain")
        # Simulation: Domain zur Blacklist hinzufügen
        return jsonify({"status": "success", "message": f"{neue_domain} added to blacklist!"})
    return render_template("blacklist.html")

@app.route("/lists", methods=["GET", "POST"])
def lists():
    if request.method == "POST":
        neue_url = request.form.get("url")
        # Simulation: URL zur Hosts-Liste hinzufügen
        return jsonify({"status": "success", "message": f"{neue_url} added to hosts list!"})
    return render_template("lists.html", lists=STATISTIK["list_bewertung"])

@app.route("/start-tests", methods=["POST"])
def start_tests():
    # Simulation: Domain-Test starten
    starte_domain_tests()
    return jsonify({"status": "success", "message": "Domain tests started!"})

@app.route("/logs")
def logs():
    # Simulation: Logs anzeigen
    logs = [
        {"timestamp": datetime.now().isoformat(), "level": "INFO", "message": "Test started."},
        {"timestamp": datetime.now().isoformat(), "level": "ERROR", "message": "Failed to resolve domain."},
    ]
    return render_template("logs.html", logs=logs)

@app.route('/test_domain', methods=['POST'])
def test_domain():
    data = request.json
    domain = data.get('domain', '').strip()
    if not ist_gueltige_domain(domain):
        return jsonify({"message": "Invalid domain format"}), 400

    reachable = test_dns_entry(domain)
    status = "reachable" if reachable else "unreachable"
    return jsonify({"domain": domain, "status": status})

@app.route('/start_log_stream', methods=['POST'])
def start_log_stream():
    threading.Thread(target=log_streamer, daemon=True).start()
    return jsonify({"message": "Log streaming started"})

@app.route('/update_batch_progress', methods=['POST'])
def update_batch_progress():
    data = request.json
    batch_progress["current"] = data.get("current", 0)
    batch_progress["total"] = data.get("total", 0)
    return jsonify({"message": "Progress updated"})

@app.route('/get_batch_progress', methods=['GET'])
def get_batch_progress():
    return jsonify(batch_progress)

@app.route('/update_batch_progress', methods=['POST'])
def update_batch_progress():
    data = request.json
    batch_progress["current"] = data.get("current", 0)
    batch_progress["total"] = data.get("total", 0)
    return jsonify({"message": "Progress updated"})

@app.route('/get_batch_progress', methods=['GET'])
def get_batch_progress():
    return jsonify(batch_progress)

@app.route('/dns_config', methods=['POST'])
def dns_config():
    data = request.json
    CONFIG['dns_server_list'] = data.get('dns_servers', [])
    with open(os.path.join(skript_verzeichnis, 'config.json'), 'w') as config_file:
        json.dump(CONFIG, config_file, indent=4)
    return jsonify({"message": "DNS configuration updated"})


@app.route('/log_block', methods=['POST'])
def log_block():
    data = request.json
    entry = {
        "domain": data.get("domain"),
        "status": data.get("status"),  # 'blocked' or 'allowed'
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    }
    block_log.append(entry)
    return jsonify({"message": "Log entry added", "entry": entry})

@app.route('/get_block_log', methods=['GET'])
def get_block_log():
    return jsonify(block_log)

@app.route('/stats_summary', methods=['GET'])
def stats_summary():
    blocked = len([log for log in block_log if log["status"] == "blocked"])
    allowed = len([log for log in block_log if log["status"] == "allowed"])
    return jsonify({
        "blocked": blocked,
        "allowed": allowed,
        "total": blocked + allowed
    })

@app.route('/api/blocking_status', methods=['GET'])
def api_blocking_status():
    domain = request.args.get('domain', '').strip()
    if not ist_gueltige_domain(domain):
        return jsonify({"error": "Invalid domain format"}), 400

    reachable = test_dns_entry(domain)
    return jsonify({"domain": domain, "reachable": reachable})

@app.route('/api/add_whitelist', methods=['POST'])
def api_add_whitelist():
    data = request.json
    domain = data.get("domain", "").strip()
    if not ist_gueltige_domain(domain):
        return jsonify({"error": "Invalid domain format"}), 400

    with open(os.path.join(skript_verzeichnis, 'whitelist.txt'), 'a') as whitelist_file:
        whitelist_file.write(f"{domain}\n")

    return jsonify({"message": f"Domain {domain} added to whitelist"})

@app.route('/api/get_whitelist', methods=['GET'])
def api_get_whitelist():
    try:
        with open(os.path.join(skript_verzeichnis, 'whitelist.txt'), 'r') as file:
            whitelist = [line.strip() for line in file if line.strip()]
        return jsonify({"whitelist": whitelist})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/remove_whitelist', methods=['POST'])
def api_remove_whitelist():
    data = request.json
    domain = data.get("domain", "").strip()
    if not ist_gueltige_domain(domain):
        return jsonify({"error": "Invalid domain format"}), 400

    whitelist_path = os.path.join(skript_verzeichnis, 'whitelist.txt')
    try:
        with open(whitelist_path, 'r') as file:
            whitelist = [line.strip() for line in file if line.strip()]
        
        if domain not in whitelist:
            return jsonify({"error": f"Domain {domain} not found in whitelist"}), 404
        
        whitelist.remove(domain)
        with open(whitelist_path, 'w') as file:
            file.write("\n".join(whitelist) + "\n")
        
        return jsonify({"message": f"Domain {domain} removed from whitelist"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/add_blacklist', methods=['POST'])
def api_add_blacklist():
    data = request.json
    domain = data.get("domain", "").strip()
    if not ist_gueltige_domain(domain):
        return jsonify({"error": "Invalid domain format"}), 400

    with open(os.path.join(skript_verzeichnis, 'blacklist.txt'), 'a') as blacklist_file:
        blacklist_file.write(f"{domain}\n")

    return jsonify({"message": f"Domain {domain} added to blacklist"})

@app.route('/api/get_blacklist', methods=['GET'])
def api_get_blacklist():
    try:
        with open(os.path.join(skript_verzeichnis, 'blacklist.txt'), 'r') as file:
            blacklist = [line.strip() for line in file if line.strip()]
        return jsonify({"blacklist": blacklist})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/remove_blacklist', methods=['POST'])
def api_remove_blacklist():
    data = request.json
    domain = data.get("domain", "").strip()
    if not ist_gueltige_domain(domain):
        return jsonify({"error": "Invalid domain format"}), 400

    blacklist_path = os.path.join(skript_verzeichnis, 'blacklist.txt')
    try:
        with open(blacklist_path, 'r') as file:
            blacklist = [line.strip() for line in file if line.strip()]
        
        if domain not in blacklist:
            return jsonify({"error": f"Domain {domain} not found in blacklist"}), 404
        
        blacklist.remove(domain)
        with open(blacklist_path, 'w') as file:
            file.write("\n".join(blacklist) + "\n")
        
        return jsonify({"message": f"Domain {domain} removed from blacklist"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Hauptprogramm
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
