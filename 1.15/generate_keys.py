# generate_keys.py
import random
import string
def generate_keys(n=100):
    keys = []
    for _ in range(n):
        key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
        formatted_key = '-'.join([key[i:i+4] for i in range(0, 16, 4)])
        keys.append(f'"{formatted_key}"')
    return keys
keys = generate_keys()
for k in keys:
    print(k, end=',\n')
