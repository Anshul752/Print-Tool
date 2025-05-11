# app.py (FINAL VERSION with Licensed PC IDs in Trial+activation auto update Admin Panel)

from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import json
import threading

app = Flask(__name__)
LOCK = threading.Lock()

KEYS_FILE = "keys.json"

def load_keys():
    with open(KEYS_FILE, "r") as f:
        return json.load(f)

def save_keys(data):
    with open(KEYS_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route('/validate', methods=['POST'])
def validate_key():
    key = request.form.get("key")
    pc_id = request.form.get("pc_id")

    with LOCK:
        data = load_keys()

        if key not in data["keys"]:
            return jsonify({"status": "invalid"})

        record = data["keys"][key]

        if record["used"]:
            if record["pc_id"] == pc_id:
                return jsonify({"status": "success"})
            else:
                return jsonify({"status": "already_used"})
        else:
            record["used"] = True
            record["pc_id"] = pc_id
            save_keys(data)
            return jsonify({"status": "success"})

@app.route('/trial_check', methods=['POST'])
def trial_check():
    pc_id = request.form.get("pc_id")

    with LOCK:
        data = load_keys()
        if pc_id in data["trial_pc_ids"]:
            return jsonify({"trial_used": True})
        return jsonify({"trial_used": False})

@app.route('/start_trial', methods=['POST'])
def start_trial():
    pc_id = request.form.get("pc_id")

    with LOCK:
        data = load_keys()
        if pc_id not in data["trial_pc_ids"]:
            data["trial_pc_ids"].append(pc_id)
            save_keys(data)
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

    with LOCK:
        keys_data = load_keys()

        # Log the status first
        print(f"[Server] Received license status: PC_ID={pc_id}, status={status}, key={license_key}")

        keys_data.setdefault("trial_pc_ids", [])

        if status.startswith("trial"):
            # === Add to trial_pc_ids ===
            if pc_id not in keys_data["trial_pc_ids"]:
                keys_data["trial_pc_ids"].append(pc_id)

            # === Remove license key activation if exists ===
            for key, info in keys_data["keys"].items():
                if info.get("pc_id") == pc_id:
                    keys_data["keys"][key]["used"] = False
                    keys_data["keys"][key]["pc_id"] = None

        elif status == "licensed" and license_key:
            # === Assign pc_id to license key ===
            if license_key in keys_data["keys"]:
                keys_data["keys"][license_key]["used"] = True
                keys_data["keys"][license_key]["pc_id"] = pc_id

            # === Remove from trial_pc_ids ===
            if pc_id in keys_data["trial_pc_ids"]:

        save_keys(keys_data)

    return jsonify({"status": "received"})

@app.route('/')
def home():
    return "License Server Running ✅"

@app.route('/admin')
def admin_panel():
    with LOCK:
        data = load_keys()
        keys = data.get("keys", {})
        trial_pc_ids = data.get("trial_pc_ids", [])
        licensed_pc_ids = data.get("licensed_pc_ids", {})
        reset_required_pc_ids = data.get("reset_required_pc_ids", [])

    html = '''
    <h2>🔑 License Keys and Trial PCs Overview (Admin Panel)</h2>

    <form action="/admin/reset" method="post">
      <label><b>Enter PC ID to Reset:</b></label><br>
      <input type="text" name="pc_id" required style="width:300px">
      <br><br>
      <button type="submit" name="action" value="reset_trial">🗑️ Reset Trial</button>
      <button type="submit" name="action" value="reset_key">🗑️ Reset Key Activation</button>
    </form>

    <br><br>

    <form action="/admin/add_reset_required" method="post">
      <label><b>Enter PC ID to Add to Reset Required:</b></label><br>
      <input type="text" name="pc_id" required style="width:300px">
      <br><br>
      <div style="display:flex; gap:10px;">
        <button type="submit" name="action" value="add_reset_required">➕ Add to Reset Required</button>
        <button type="submit" name="action" value="remove_reset_required">➖ Remove from Reset Required</button>
      </div>
    </form>

    <br><br>

    <input type="text" id="searchBox" onkeyup="filterTables()" placeholder="🔍 Search License Key or PC ID" style="width:400px; padding:5px">

    <br><br>

    <div style="display:flex; gap:40px; flex-wrap:wrap;">

      <div>
        <h3>🔐 License Keys</h3>
        <table border="1" cellpadding="5" id="keysTable">
          <tr>
            <th>License Key</th><th>Used?</th><th>✅ Licensed PC IDs</th>
          </tr>
          {% for key, info in keys.items() %}
          <tr>
            <td>{{ key }}</td>
            <td>{{ 'Yes' if info['used'] else 'No' }}</td>
            <td>{{ info['pc_id'] if info['pc_id'] else '-' }}</td>
          </tr>
          {% endfor %}
        </table>
      </div>

      <div>
        <h3>🖥️ Trial PC IDs</h3>
        <table border="1" cellpadding="5" id="trialTable">
          <tr><th>Trial PC ID</th></tr>
          {% for pc_id in trial_pc_ids %}
          <tr><td>{{ pc_id }}</td></tr>
          {% endfor %}
        </table>
      </div>


       <div>
         <h3>🔄 Reset Required PC IDs</h3>
         <table border="1" cellpadding="5" id="resetRequiredTable">
           <tr><th>PC ID</th></tr>
           {% for pc_id in reset_required_pc_ids %}
           <tr><td>{{ pc_id }}</td></tr>
           {% endfor %}
         </table>
       </div>

    </div>

    <script>
    function filterTables() {
      let input = document.getElementById("searchBox");
      let filter = input.value.toUpperCase();

      let tables = ["keysTable", "trialTable", "licensedTable", "resetRequiredTable"];
      for (let t of tables) {
        let table = document.getElementById(t);
        let rows = table.getElementsByTagName("tr");
        for (let i = 1; i < rows.length; i++) {
          let cells = rows[i].getElementsByTagName("td");
          let match = false;
          for (let c of cells) {
            let text = c.textContent || c.innerText;
            if (text.toUpperCase().indexOf(filter) > -1) {
              match = true;
              break;
            }
          }
          rows[i].style.display = match ? "" : "none";
        }
      }
    }
    </script>
    '''

    return render_template_string(html, keys=keys, trial_pc_ids=trial_pc_ids, licensed_pc_ids=licensed_pc_ids, reset_required_pc_ids=reset_required_pc_ids)

@app.route('/admin/reset', methods=['POST'])
def admin_reset():
    pc_id = request.form.get("pc_id").strip()
    action = request.form.get("action")

    with LOCK:
        data = load_keys()

        if action == "reset_trial":
            if pc_id in data['trial_pc_ids']:
                data['trial_pc_ids'].remove(pc_id)
                save_keys(data)

        elif action == "reset_key":
            keys_updated = False
            for key, info in data['keys'].items():
                if info['pc_id'] == pc_id:
                    data['keys'][key]['used'] = False
                    data['keys'][key]['pc_id'] = None
                    keys_updated = True
            if keys_updated:
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
