
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/stats')
def stats():
    return jsonify({"blocked_requests": 120, "allowed_requests": 300})

if __name__ == '__main__':
    app.run(debug=True)
