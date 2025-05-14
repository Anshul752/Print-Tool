# app.py (FINAL VERSION with Licensed PC IDs in Trial+activation auto update Modern Admin Panel working,duplicate key removed)
# admin password, user data also update

from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import json
import threading
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
LOCK = threading.Lock()

KEYS_FILE = "keys.json"

def load_keys():
    with open(KEYS_FILE, "r") as f:
        return json.load(f)

def save_keys(data):
    with open(KEYS_FILE, "w") as f:
        json.dump(data, f, indent=2)
        
@app.route('/')
def health_check():
    return "✅ Service is running Test ENV ", 200

from datetime import datetime

@app.route('/validate', methods=['POST'])
def validate_key():
    data = request.get_json()
    key = data.get("key")
    pc_id = data.get("pc_id")
    user_info = data.get("user_info")
    activated_on = data.get("activated_on")

    with LOCK:
        keys_data = load_keys()

        if key not in keys_data["keys"]:
            return jsonify({"status": "invalid"})

        record = keys_data["keys"][key]

        if record["used"]:
            if record["pc_id"] == pc_id:
                return jsonify({"status": "success"})
            else:
                return jsonify({"status": "already_used"})
        else:
            # === Auto-remove any old key linked to this PC ===
            for other_key, other_record in keys_data["keys"].items():
                if other_record["pc_id"] == pc_id and other_key != key:
                    other_record["used"] = False
                    other_record["pc_id"] = "-"
                    keys_data.get("activation_dates", {}).pop(other_key, None)
                    keys_data["keys"][other_key].pop("user_info", None)

                    

            # === Activate current key ===
            record["used"] = True
            record["pc_id"] = pc_id

            if user_info:
                record["user_info"] = {
                    "first_name": user_info.get("first_name", ""),
                    "mobile_number": user_info.get("mobile_number", ""),
                    "shop_name": user_info.get("shop_name", ""),
                    "city": user_info.get("city", "")
                }

            if activated_on:
                keys_data.setdefault("activation_dates", {})
                keys_data["activation_dates"][key] = activated_on

            save_keys(keys_data)
            return jsonify({"status": "success"})

@app.route('/trial_check', methods=['POST'])
def trial_check():
    pc_id = request.form.get("pc_id")

    with LOCK:
        data = load_keys()
        if pc_id in data["trial_pc_ids"]:
            return jsonify({"trial_used": True})
        return jsonify({"trial_used": False})
        
from datetime import datetime

@app.route('/start_trial', methods=['POST'])
def start_trial():
    data = request.get_json()
    pc_id = data.get("pc_id")
    user_info = data.get("user_info")
    trial_start = data.get("trial_start")
    days_left = data.get("days_left")  # NEW FIELD

    with LOCK:
        keys_data = load_keys()

        keys_data.setdefault("trial_pc_ids", [])
        keys_data.setdefault("trial_user_info", {})
        keys_data.setdefault("trial_dates", {})
        keys_data.setdefault("trial_days_left", {})  # NEW FIELD

        if pc_id not in keys_data["trial_pc_ids"]:
            keys_data["trial_pc_ids"].append(pc_id)

        if user_info:
            keys_data["trial_user_info"][pc_id] = {
                "first_name": user_info.get("first_name", ""),
                "mobile_number": user_info.get("mobile_number", ""),
                "shop_name": user_info.get("shop_name", ""),
                "city": user_info.get("city", "")
            }

        if trial_start:
            keys_data["trial_dates"][pc_id] = trial_start

        save_keys(keys_data)
        return jsonify({"status": "trial_started"})

@app.route('/reset_check', methods=['POST'])
def reset_check():
    pc_id = request.form.get("pc_id")

    with LOCK:
        data = load_keys()
        reset_list = data.get("reset_required_pc_ids", [])
        is_reset_required = pc_id in reset_list

        if is_reset_required:
            reset_list.remove(pc_id)
            data["reset_required_pc_ids"] = reset_list
            save_keys(data)

    return jsonify({"reset_required": is_reset_required})

@app.route("/update_status", methods=["POST"])
def update_status():
    data = request.get_json()
    pc_id = data.get("pc_id")
    status = data.get("status")
    license_key = data.get("license_key")
    user_info = data.get("user_info")
    trial_start = data.get("trial_start")
    activated_on = data.get("activated_on")

    with LOCK:
        keys_data = load_keys()

        print(f"[Server] Received Data by update_status : PC_ID={pc_id}, status={status}, key={license_key}, user_info as {user_info}")

        keys_data.setdefault("trial_pc_ids", [])
        keys_data.setdefault("trial_user_info", {})
        keys_data.setdefault("trial_dates", {})  # <-- NEW for storing trial_start
        keys_data.setdefault("activation_dates", {})  # <-- NEW for storing activated_on

        if status.startswith("trial"):
            if pc_id not in keys_data["trial_pc_ids"]:
                keys_data["trial_pc_ids"].append(pc_id)

            if user_info:
                keys_data["trial_user_info"][pc_id] = {
                    "first_name": user_info.get("first_name", ""),
                    "mobile_number": user_info.get("mobile_number", ""),
                    "shop_name": user_info.get("shop_name", ""),
                    "city": user_info.get("city", "")
                }

            if trial_start:
                keys_data["trial_dates"][pc_id] = trial_start  # <-- SAVE trial start date

            # Remove license key association if any
            for key, info in keys_data["keys"].items():
                if info.get("pc_id") == pc_id:
                    keys_data["keys"][key]["used"] = False
                    keys_data["keys"][key]["pc_id"] = None

        elif status == "licensed" and license_key:
            if license_key in keys_data["keys"]:
                keys_data["keys"][license_key]["used"] = True
                keys_data["keys"][license_key]["pc_id"] = pc_id

                if user_info:
                    keys_data["keys"][license_key]["user_info"] = {
                        "first_name": user_info.get("first_name", ""),
                        "mobile_number": user_info.get("mobile_number", ""),
                        "shop_name": user_info.get("shop_name", ""),
                        "city": user_info.get("city", "")
                    }

                if activated_on:
                    keys_data["activation_dates"][license_key] = activated_on  # <-- SAVE activation date

        save_keys(keys_data)

    return jsonify({"status": "received"})

auth = HTTPBasicAuth()

# Load username and password from config file
with open('admin_auth.json') as f:
    admin_creds = json.load(f)

# Store hashed password (optional but safer)
ADMIN_USERNAME = admin_creds["username"]
ADMIN_PASSWORD_HASH = generate_password_hash(admin_creds["password"])

@auth.verify_password
def verify_password(username, password):
    if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
        return username

@app.route('/admin')
@auth.login_required
def admin_panel():
    with LOCK:
        data = load_keys()
        keys = data.get("keys", {})
        trial_pc_ids = data.get("trial_pc_ids", [])
        licensed_pc_ids = data.get("licensed_pc_ids", {})
        reset_required_pc_ids = data.get("reset_required_pc_ids", [])
        trial_user_info = data.get("trial_user_info", {})
        activation_dates = data.get("activation_dates", {})
        trial_dates = data.get("trial_dates", {}) 
        
        trial_days_left = {}
        for pc_id, start_str in trial_dates.items():
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d")
                days_passed = (datetime.now() - start_date).days
                trial_days_left[pc_id] = max(0, 30 - days_passed)
            except Exception:
                trial_days_left[pc_id] = "-"
    html = '''
    <html>
    <head>
    <style>
      body {
        font-family: 'Segoe UI', Tahoma, sans-serif;
        background-color: #f0f4f8;
        color: #333;
        padding: 30px;
      }
    
      h2 {
        color: #0a66c2;
        margin-bottom: 20px;
      }
    
      .forms-container {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        flex-wrap: wrap;
        margin-bottom: 30px;
      }
    
      form {
        background: #ffffff;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        flex: 1 1 300px;
        min-width: 260px;
      }
    
      label {
        display: block;
        margin-bottom: 8px;
        font-weight: 600;
      }
    
      input[type="text"] {
        width: 100%;
        padding: 10px;
        border: 1px solid #ccd6dd;
        border-radius: 8px;
        margin-bottom: 15px;
        box-sizing: border-box;
      }
    
      button {
        background-color: #0a66c2;
        color: white;
        border: none;
        padding: 8px 14px;
        border-radius: 8px;
        cursor: pointer;
        transition: background 0.2s;
        font-size: 14px;
      }
    
      button:hover {
        background-color: #004e9a;
      }
    
      .button-group {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
      }
    
      #searchBox {
        width: 400px;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #ccd6dd;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 15px;
      }
    
      select {
        padding: 6px;
        border-radius: 6px;
        border: 1px solid #ccd6dd;
        margin-bottom: 10px;
      }
    
      .tables-container {
        display: flex;
        gap: 30px;
        flex-wrap: wrap;
        margin-top: 30px;
      }
    
      .table-card {
        background: #ffffff;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        flex: 1 1 300px;
        min-width: 280px;
      }
    
      table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
      }
    
      th, td {
        padding: 8px 10px;
        border-bottom: 1px solid #e0e6ed;
        text-align: left;
        font-size: 14px;
      }
    
      th {
        background-color: #f5f7fa;
        font-weight: 600;
      }
    
      tr:hover {
        background-color: #f0f8ff;
      }
    </style>
    </head>
    <body>
    
    <h2>🔑 License Keys and Trial PCs Overview (Admin Panel)</h2>
    
    <div class="forms-container">
    
      <!-- Left -->
      <form action="/admin/reset" method="post">
        <label>Enter PC ID to Reset:</label>
        <input type="text" name="pc_id" required>
        <div class="button-group">
          <button type="submit" name="action" value="reset_trial">🗑️ Reset Trial</button>
          <button type="submit" name="action" value="reset_key">🗑️ Reset Key Activation</button>
        </div>
      </form>
    
      <!-- Center -->
      <form action="/admin/add_reset_required" method="post">
        <label>Enter PC ID to Add to Reset Required:</label>
        <input type="text" name="pc_id" required>
        <div class="button-group">
          <button type="submit" name="action" value="add_reset_required">➕ Add to Reset Required</button>
          <button type="submit" name="action" value="remove_reset_required">➖ Remove from Reset Required</button>
        </div>
      </form>
    
      <!-- Right -->
      <div class="table-card">
        <h3>🔄 Reset Required PC IDs</h3>
        <table id="resetRequiredTable">
          <tr><th>PC ID</th></tr>
          {% for pc_id in reset_required_pc_ids %}
          <tr><td>{{ pc_id }}</td></tr>
          {% endfor %}
        </table>
      </div>
    
    </div>
    
    <input type="text" id="searchBox" onkeyup="filterTables()" placeholder="🔍 Search License Key or PC ID">
    
    <div class="tables-container">
    
      <div class="table-card">
        <h3>🔐 License Keys</h3>
    
        <label for="usedFilter"><b>Filter by Used Status:</b></label>
        <select id="usedFilter" onchange="filterTables()">
          <option value="all">All</option>
          <option value="yes" selected>Used</option>
          <option value="no">Unused</option>
        </select>
    
        <table id="keysTable">
          <tr>
            <th>License Key</th>
            <th>Used?</th>
            <th>Licensed PC ID</th>
            <th>Name</th>
            <th>Mobile</th>
            <th>Shop</th>
            <th>City</th>
            <th>Activation Date</th>
          </tr>
          {% for key, info in keys.items() %}
          <tr>
            <td>{{ key }}</td>
            <td>{{ 'Yes' if info['used'] else 'No' }}</td>
            <td>{{ info['pc_id'] if info['pc_id'] else '-' }}</td>
            <td>{{ info.get('user_info', {}).get('first_name', '-') }}</td>
            <td>{{ info.get('user_info', {}).get('mobile_number', '-') }}</td>
            <td>{{ info.get('user_info', {}).get('shop_name', '-') }}</td>
            <td>{{ info.get('user_info', {}).get('city', '-') }}</td>
            <td>{{ activation_dates.get(key, '-') }}</td>
          </tr>
          {% endfor %}
        </table>
      </div>
    
      <div class="table-card">
        <h3>🖥️ Trial PC IDs</h3>
        <table id="trialTable">
          <tr>
            <th>Trial PC ID</th>
            <th>Name</th>
            <th>Mobile</th>
            <th>Shop</th>
            <th>City</th>
            <th>Trial Date</th>
            <th>Days Left</th>
          </tr>
          {% for pc_id in trial_pc_ids %}
          <tr>
            <td>{{ pc_id }}</td>
            <td>{{ trial_user_info.get(pc_id, {}).get('first_name', '-') }}</td>
            <td>{{ trial_user_info.get(pc_id, {}).get('mobile_number', '-') }}</td>
            <td>{{ trial_user_info.get(pc_id, {}).get('shop_name', '-') }}</td>
            <td>{{ trial_user_info.get(pc_id, {}).get('city', '-') }}</td>
            <td>{{ trial_dates.get(pc_id, '-') }}</td>
            <td>{{ trial_days_left.get(pc_id, '-') }}</td>
          </tr>
          {% endfor %}
        </table>
      </div>
    
    </div>
    
    <script>
    function filterTables() {
      const searchInput = document.getElementById('searchBox').value.toLowerCase();
      const usedFilter = document.getElementById('usedFilter').value;
    
      const tables = ['keysTable', 'trialTable', 'resetRequiredTable'];
      tables.forEach(tableId => {
        const table = document.getElementById(tableId);
        const tr = table.getElementsByTagName('tr');
    
        for (let i = 1; i < tr.length; i++) {
          const rowText = tr[i].textContent.toLowerCase();
          let showRow = rowText.includes(searchInput);
    
          if (tableId === 'keysTable' && usedFilter !== 'all') {
            const usedCell = tr[i].getElementsByTagName('td')[1];
            const usedText = usedCell.textContent.trim().toLowerCase();
            const isUsed = (usedText === 'yes');
            if (usedFilter === 'yes' && !isUsed) showRow = false;
            if (usedFilter === 'no' && isUsed) showRow = false;
          }
    
          tr[i].style.display = showRow ? '' : 'none';
        }
      });
    }
    
    // Apply filter on page load
    window.onload = function() {
      filterTables();
    };
    </script>
    
    </body>
    </html>
    '''

    return render_template_string(html,keys=keys,trial_pc_ids=trial_pc_ids,licensed_pc_ids=licensed_pc_ids,reset_required_pc_ids=reset_required_pc_ids,
                                  trial_user_info=trial_user_info,activation_dates=activation_dates,trial_dates=trial_dates,trial_days_left=trial_days_left)

@app.route('/admin/reset', methods=['POST']) 
def admin_reset():
    pc_id = request.form.get("pc_id").strip()
    action = request.form.get("action")

    with LOCK:
        data = load_keys()

        if action == "reset_trial":
            if pc_id in data.get('trial_pc_ids', []):
                data['trial_pc_ids'].remove(pc_id)

            # Also remove trial user info and trial date
            trial_user_info = data.get("trial_user_info", {})
            trial_dates = data.get("trial_dates", {})

            trial_user_info.pop(pc_id, None)
            trial_dates.pop(pc_id, None)

            data["trial_user_info"] = trial_user_info
            data["trial_dates"] = trial_dates

        elif action == "reset_key":
            keys_updated = False
            activation_dates = data.get("activation_dates", {})

            for key, info in data.get("keys", {}).items():
                if info.get("pc_id") == pc_id:
                    info["used"] = False
                    info["pc_id"] = None
                    info["user_info"] = {}
                    activation_dates.pop(key, None)
                    keys_updated = True

            data["activation_dates"] = activation_dates

        save_keys(data)

    return redirect(url_for('admin_panel'))


@app.route('/admin/add_reset_required', methods=['POST'])
def add_reset_required():
    pc_id = request.form.get("pc_id").strip()
    action = request.form.get("action")

    with LOCK:
        data = load_keys()

        if action == "add_reset_required":
            if pc_id not in data.get('reset_required_pc_ids', []):
                data['reset_required_pc_ids'].append(pc_id)
                save_keys(data)

        elif action == "remove_reset_required":
            if pc_id in data.get('reset_required_pc_ids', []):
                data['reset_required_pc_ids'].remove(pc_id)
                save_keys(data)

    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
