from flask import Flask, jsonify, request
from backend.core.domain_tester import start_domain_tests
from backend.core.git_handler import push_to_git
from backend.utils.logger import initialize_logger

app = Flask(__name__)

# Initialisiere das Logger
initialize_logger()

@app.route('/start-tests', methods=['POST'])
def start_tests():
    data = request.get_json()
    sources = data.get('sources', [])
    if not sources:
        return jsonify({"error": "No sources provided"}), 400
    result = start_domain_tests(sources)
    return jsonify({"message": "Tests started", "result": result}), 200

@app.route('/push-to-git', methods=['POST'])
def push_git():
    message = request.get_json().get('message', 'Auto-commit')
    push_to_git(message)
    return jsonify({"message": "Changes pushed to Git"}), 200

@app.route('/logs', methods=['GET'])
def get_logs():
    with open('logs/app.log', 'r') as log_file:
        logs = log_file.read()
    return jsonify({"logs": logs}), 200

if __name__ == '__main__':
    app.run(debug=True)
