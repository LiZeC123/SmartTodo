import random
import string


def generate_token_str():
    return ''.join(random.sample(string.ascii_letters + string.digits, 16))