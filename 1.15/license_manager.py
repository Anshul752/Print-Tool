# license_manager.py 
import os
import json
import uuid
import platform
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from license_keys import VALID_KEYS

LICENSE_FILE = "license.dat"
FERNET_KEY = b'_b1Wy08vEsmGd4F88TCL0XUl3ayDGoUHYodEcR_8AE8='  # FIXED SECRET KEY
fernet = Fernet(FERNET_KEY)
TRIAL_PERIOD_DAYS = 3
 
def get_pc_id():
    """Generate a consistent unique PC ID based on hardware"""
    try:
        if platform.system() == "Windows":
            # Use disk serial number (safe & consistent)
            from subprocess import check_output
            output = check_output('wmic diskdrive get SerialNumber', shell=True).decode()
            lines = output.strip().split('\n')
            serials = [line.strip() for line in lines[1:] if line.strip()]
            return serials[0] if serials else str(uuid.getnode())  # fallback
        else:
            # For Linux/Mac fallback to MAC address
            return str(uuid.getnode())
    except:
        return str(uuid.getnode())  # fallback MAC
 
def encrypt_data(data):
    # Ensure datetime is ISO string
    if data.get("trial_start") and isinstance(data["trial_start"], datetime):
        data["trial_start"] = data["trial_start"].isoformat()
    json_data = json.dumps(data).encode()
    encrypted = fernet.encrypt(json_data)
    return encrypted
 
def decrypt_data(encrypted_data):
    decrypted = fernet.decrypt(encrypted_data)
    return json.loads(decrypted)
 
def unhide_license_file(file_path="license.dat"):
    """Remove Hidden + Read-only attributes before writing"""
    if platform.system() == "Windows":
        os.system(f'attrib -h -r "{file_path}"')
 
def hide_license_file(file_path="license.dat"):
    """Set Hidden + Read-only attributes after writing"""
    if platform.system() == "Windows":
        os.system(f'attrib +h +r "{file_path}"')
 
def save_data(data, filename='license.dat'):
    # Before writing → remove protection (if file exists)
    if os.path.exists(filename):
        unhide_license_file(filename)
 
    # Write encrypted data
    with open(filename, 'wb') as f:
        f.write(encrypt_data(data))

    # After writing → re-apply protection
    hide_license_file(filename)
 
def load_data():
    with open(LICENSE_FILE, "rb") as f:
        encrypted_data = f.read()
    return decrypt_data(encrypted_data)
 
def initialize_license_file():
    data = {
        "status": "none",
        "trial_start": None,
        "license_key": None,
        "pc_id": get_pc_id()}
    save_data(data)
 
def activate_license(key):
    if key in VALID_KEYS:
        data = {
            "status": "licensed",
            "trial_start": None,
            "license_key": key,
            "pc_id": get_pc_id()}
        save_data(data)
        return True
    return False
 
def start_trial():
    data = {
        "status": "trial",
        "trial_start": datetime.now().isoformat(),
        "license_key": None,
        "pc_id": get_pc_id()}
    save_data(data)

def is_license_valid():
    if not os.path.exists(LICENSE_FILE):
        initialize_license_file()
    try:
        data = load_data()
    except Exception:
        initialize_license_file()
        data = load_data()
    current_pc_id = get_pc_id()
    
    # Check PC binding first
    if data.get("pc_id") != current_pc_id:
        return False  # Block usage on other PC
    
    if data["status"] == "licensed":
        return True
 
    elif data["status"] == "trial" and data["trial_start"]:
        trial_start = datetime.fromisoformat(data["trial_start"])
        if datetime.now() - trial_start <= timedelta(days=TRIAL_PERIOD_DAYS):
            return "trial"
        else:
            return False
    else:
        return False

 