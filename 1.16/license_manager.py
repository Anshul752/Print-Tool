# license_manager.py
import os, json, uuid, hashlib, base64, requests,sys,shutil
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter, Retry

ENCRYPTION_KEY = "IDPrintToolLicenseKey2025"
SERVER_URL = "https://id-print-tool.onrender.com/"

def get_internal_file_path(filename):
    """Return absolute path to file inside 'system' folder."""
    base_path = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
    internal_folder = os.path.join(base_path, "system")
    os.makedirs(internal_folder, exist_ok=True)
    return os.path.join(internal_folder, filename)
 
# Usage
LICENSE_FILE = get_internal_file_path("license_info.json")
TRIAL_MARKER_FILE = get_internal_file_path(".trial_used")

# === PC ID ===
def get_pc_identifier():
    node = uuid.getnode()
    os_info = os.name
    raw_string = f"{node}{os_info}"
    hash_obj = hashlib.sha256(raw_string.encode()).hexdigest()
    return hash_obj[:12]  # 12-char PC ID
 
# === Simple Encryption ===
def encrypt_data(data):
    key = ENCRYPTION_KEY.encode()
    data = data.encode()
    encrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
    return base64.b64encode(encrypted).decode()
 
def decrypt_data(data):
    key = ENCRYPTION_KEY.encode()
    data = base64.b64decode(data.encode())
    decrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
    return decrypted.decode()
 
def save_license_info(info):
    encrypted = encrypt_data(json.dumps(info))
    with open(LICENSE_FILE, "w") as f:
        f.write(encrypted)
 
def load_license_info():
    if os.path.exists(LICENSE_FILE):
        try:
            with open(LICENSE_FILE, "r") as f:
                encrypted = f.read()
            decrypted = decrypt_data(encrypted)
            return json.loads(decrypted)
        except Exception as e:
            print(f"Failed to load license info: {e}")
    return {}
 
# === Trial Calculation ===
def calculate_trial_days_left(info):
    start_date = datetime.strptime(info.get("trial_start", ""), "%Y-%m-%d")
    today = datetime.now()
    if today < start_date:
        return -1  # System date rollback detected
    days_passed = (today - start_date).days
    return max(0, 30 - days_passed)
 
# === Status Check ===
def is_license_valid():
    info = load_license_info()
    if info.get("blocked"):
        return "blocked"
    if info.get("status") == "activated":
        if info.get("pc_id") == get_pc_identifier():
            return "licensed"
        else:
            return "blocked"

    if info.get("status") == "trial":
        trial_days_left = calculate_trial_days_left(info)

        if trial_days_left == -1:
            info["blocked"] = True
            save_license_info(info)
            return "blocked"
        if trial_days_left > 0:
            return f"trial_{trial_days_left}"
        else:
            return "expired"
    return None
 
# === Activation ===
def activate_license(key):
    pc_id = get_pc_identifier()
 
    # --- Setup session with retries ---
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[502, 503, 504],
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
 
    # --- Call validate API ---
    try:
        response = session.post(f"{SERVER_URL}/validate", data={"key": key, "pc_id": pc_id}, timeout=10)
        response.raise_for_status()
        result = response.json()
 
        if result.get("status") == "success":
            info = {
                "key": key,
                "pc_id": pc_id,
                "status": "activated",
                "activated_on": datetime.now().strftime("%Y-%m-%d"),
                "blocked": False
            }
            save_license_info(info)
            return True
        else:
            return "invalid"
 
    except Exception as e:
        print(f"❌ Activation failed (after retries): {e}")
        return "connection_error"
 
# === Start Trial ===
def start_trial():
    pc_id = get_pc_identifier()
    # --- Setup session with retries ---
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=2,  # 2s, 4s, 8s
        status_forcelist=[502, 503, 504],
        allowed_methods=["POST"])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    # --- Step 1: Check if trial already used (server MUST be reachable) ---
    try:
        response = session.post(f"{SERVER_URL}/trial_check", data={"pc_id": pc_id}, timeout=10)
        response.raise_for_status()  # Raise exception if not 200 OK
        result = response.json()
        if result.get("trial_used"):
            return "server_blocked"
    except Exception as e:
        print(f"❌ Trial server check failed (after retries): {e}")
        return None  # DO NOT create local marker
    # --- Step 2: Check local trial marker ---
    if os.path.exists(TRIAL_MARKER_FILE):
        return False
    # --- Step 3: Start trial locally (ONLY IF server was reachable) ---
    info = {
        "trial_start": datetime.now().strftime("%Y-%m-%d"),
        "pc_id": pc_id,
        "status": "trial",
        "blocked": False}
    save_license_info(info)
    with open(TRIAL_MARKER_FILE, "w") as f:
        f.write("trial_started")
    # --- Step 4: Notify server trial started (optional best effort) ---
    try:
        session.post(f"{SERVER_URL}/start_trial", data={"pc_id": pc_id}, timeout=10)
    except Exception as e:
        print(f"⚠️ Trial start notify failed (after retries): {e}")
    return "started"
 
# === Local Helpers ===
def block_license():
    info = load_license_info()
    info["blocked"] = True
    save_license_info(info)
 
def is_trial_active():
    info = load_license_info()
    return info.get("status") == "trial" and calculate_trial_days_left(info) > 0
 
def is_activated():
    info = load_license_info()
    return info.get("status") == "activated"

def check_and_delete_license_file():
    pc_id = get_pc_identifier()
 
    # --- Setup session with retries ---
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[502, 503, 504],
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
 
    try:
        response = session.post(f"{SERVER_URL}/reset_check", data={"pc_id": pc_id}, timeout=10)
        response.raise_for_status()
        result = response.json()
 
        if result.get("reset_required"):
            # Delete LICENSE_FILE if it exists
            if os.path.exists(LICENSE_FILE):
                os.remove(LICENSE_FILE)
            # Delete TRIAL_MARKER_FILE if it exists
            if os.path.exists(TRIAL_MARKER_FILE):
                os.remove(TRIAL_MARKER_FILE)
            # Get the _internal folder path
            internal_folder = os.path.dirname(LICENSE_FILE)
            # Delete the _internal folder (and all its contents)
            if os.path.exists(internal_folder):
                shutil.rmtree(internal_folder)
 
            # Notify server reset is done
            session.post(f"{SERVER_URL}/ack_reset_done", data={"pc_id": pc_id}, timeout=10)
 
    except Exception as e:
        print(f"[Reset check failed]: {e}")
        
def get_stored_license_key():
    info = load_license_info()
    return info.get("key") if info.get("status") == "activated" else None

def update_license_status_on_server():
    pc_id = get_pc_identifier()
    status = is_license_valid()  # returns "licensed", "trial_xxx", "expired", "blocked", etc. or None
    license_key = get_stored_license_key()  # You need to fetch stored key (if available)
 
    # Normalize status safely
    if status and status.startswith("trial"):
        normalized_status = "trial"
    elif status:
        normalized_status = status
    else:
        normalized_status = "unknown"
 
    if license_key:
        print(f"[License] Stored License Key: {license_key}")
    else:
        print("[License] No valid activated license key found")
 
    payload = {
        "pc_id": pc_id,
        "status": normalized_status,
        "license_key": license_key if normalized_status == "licensed" else None
    }
 
    # === Setup session with retries ===
    session = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=2,
        status_forcelist=[502, 503, 504],
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
 
    try:
        response = session.post(f"{SERVER_URL}/update_status", json=payload, timeout=5)
        if response.status_code == 200:
            print("[License Sync] License status updated on server.")
        else:
            print(f"[License Sync] Failed to update server (status {response.status_code})")
    except Exception as e:
        print(f"[License Sync] Error updating server: {e}")