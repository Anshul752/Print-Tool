from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)
DATA_FILE = 'license_data.json'

# Initialize file
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({"licenses": {}, "trials": {}}, f, indent=4)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/validate', methods=['POST'])
def validate_key():
    content = request.get_json()
    license_key = content.get('license_key')
    pc_id = content.get('pc_id')

    data = load_data()
    licenses = data.get('licenses', {})

    if license_key not in licenses:
        return jsonify({"status": "invalid", "message": "License key not found."})

    if licenses[license_key] is None:
        licenses[license_key] = pc_id
        data['licenses'] = licenses
        save_data(data)
        return jsonify({"status": "success", "message": "License activated successfully."})

    elif licenses[license_key] == pc_id:
        return jsonify({"status": "success", "message": "License already activated on this PC."})

    else:
        return jsonify({"status": "used_elsewhere", "message": "License key already used on another PC."})

@app.route('/trial_check', methods=['POST'])
def trial_check():
    content = request.get_json()
    pc_id = content.get('pc_id')

    data = load_data()
    trials = data.get('trials', {})

    if pc_id in trials:
        return jsonify({"status": "used"})
    else:
        return jsonify({"status": "not_used"})

@app.route('/trial_start', methods=['POST'])
def trial_start():
    content = request.get_json()
    pc_id = content.get('pc_id')

    data = load_data()
    trials = data.get('trials', {})
    trials[pc_id] = "used"
    data['trials'] = trials
    save_data(data)

    return jsonify({"status": "recorded"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
