from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)
LICENSE_DB_FILE = "license_data.json"

def load_license_data():
    if not os.path.exists(LICENSE_DB_FILE):
        with open(LICENSE_DB_FILE, "w") as f:
            json.dump({}, f)
    with open(LICENSE_DB_FILE, "r") as f:
        return json.load(f)

def save_license_data(data):
    with open(LICENSE_DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/activate_license", methods=["POST"])
def activate_license():
    req_data = request.get_json()
    license_key = req_data.get("license_key")
    pc_id = req_data.get("pc_id")

    data = load_license_data()
    if license_key not in data:
        return jsonify({"status": "invalid"})

    if data[license_key] == "":
        data[license_key] = pc_id
        save_license_data(data)
        return jsonify({"status": "success"})
    elif data[license_key] == pc_id:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "already_used"})

@app.route("/")
def home():
    return "License Server is running."

if __name__ == "__main__":
    app.run()
