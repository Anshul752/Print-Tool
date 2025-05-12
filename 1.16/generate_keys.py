# generate_keys.py
import random
import string
import json
 
def generate_license_key():
    key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    formatted_key = '-'.join([key[i:i+4] for i in range(0, 16, 4)])
    return formatted_key
 
def generate_keys_json(n=100):
    keys_data = {
        "keys": {},
        "trial_pc_ids": [],
        "reset_required_pc_ids": []  # <-- Added this line
    }
    for _ in range(n):
        key = generate_license_key()
        keys_data["keys"][key] = {"used": False, "pc_id": None}
    return keys_data
 
def save_keys_to_file(filename="license_keys.json", total_keys=100):
    keys_json = generate_keys_json(total_keys)
    with open(filename, "w") as f:
        json.dump(keys_json, f, indent=2)
    print(f"{total_keys} keys generated and saved to {filename}")
 
if __name__ == "__main__":
    save_keys_to_file(total_keys=100)  # Change number here if needed