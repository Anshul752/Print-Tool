from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)
DATA_FILE = 'license_data.json'

# Initialize license data file if not exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({}, f)

def load_license_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_license_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/validate', methods=['POST'])   # NOTICE: /validate to match client
def validate_key():
    content = request.get_json()
    license_key = content.get('license_key')
    pc_id = content.get('pc_id')

    data = load_license_data()

    if license_key not in data:
        return jsonify({"status": "invalid", "message": "License key not found."})

    if data[license_key] is None:
        # Key available, bind it to PC
        data[license_key] = pc_id
        save_license_data(data)
        return jsonify({"status": "success", "message": "License activated successfully."})

    elif data[license_key] == pc_id:
        # Already activated on same PC
        return jsonify({"status": "success", "message": "License already activated on this PC."})

    else:
        # Key bound to another PC
        return jsonify({"status": "used_elsewhere", "message": "License key already used on another PC."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
