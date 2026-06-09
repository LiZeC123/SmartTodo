import os
import random
import string


def generate_token_str():
    return "".join(random.sample(string.ascii_letters + string.digits, 32))


def get_or_create_secret_key(filepath="config/secert.txt") -> str:
    if os.path.exists(filepath):
        with open(filepath) as f:
            return f.read().strip()
    else:
        secret = generate_token_str()
        with open(filepath, "w") as f:
            f.write(secret)
        return secret
