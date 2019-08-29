import difflib
import hashlib
import json
import os
import oyaml as yaml
from cryptography.fernet import Fernet


def read_yaml(filename):
    with open(filename) as yaml_file:
        data = yaml_file.read()
    return yaml.safe_load(data)


def generate_key():
    return Fernet.generate_key().decode("utf-8")


def encrypt_data(key, content):
    is_str_data = isinstance(content, str)
    if is_str_data:
        content = content.encode("utf-8")
    fernet = Fernet(key.encode("utf-8"))
    encrypted_data = fernet.encrypt(content)
    if is_str_data:
        encrypted_data = encrypted_data.decode("utf-8")
    return encrypted_data


def decrypt_data(key, content):
    is_str_data = isinstance(content, str)
    if is_str_data:
        content = content.encode("utf-8")
    fernet = Fernet(key.encode("utf-8"))
    decrypted_data = fernet.decrypt(content)
    if is_str_data:
        decrypted_data = decrypted_data.decode("utf-8")
    return decrypted_data


def md5_hash(filename):
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as source_file:
        for chunk in iter(lambda: source_file.read(512*1024), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def md5_hash_bytes(bytes_obj):
    hash_md5 = hashlib.md5()
    for chunk in iter(lambda: bytes_obj.read(512*1024), b""):
        hash_md5.update(chunk)
    return hash_md5.hexdigest()


def md5_hash_str(string_data):
    hash_md5 = hashlib.md5()
    hash_md5.update(string_data)
    return hash_md5.hexdigest()


def list_path_recursive(path):
    for dirpath, subdirs, filenames in os.walk(path):
        for filename in filenames:
            yield os.path.join(dirpath, filename)


def compare_dicts(left, right):
    left_str = json.dumps(left, indent=2, sort_keys=True)
    right_str = json.dumps(right, indent=2, sort_keys=True)
    diff = list(difflib.unified_diff(left_str.splitlines(), right_str.splitlines(), lineterm=''))
    if diff:
        return "    " + '\n    '.join(diff)
    else:
        return None


def compare_text(left, right):
    if not isinstance(left, str):
        left = left.decode("utf-8")
    if not isinstance(right, str):
        right = right.decode("utf-8")
    diff = list(difflib.unified_diff(left.splitlines(), right.splitlines(), lineterm=''))
    if diff:
        return "    " + '\n    '.join(diff)
    else:
        return None


def update_dict_with_defaults(dct, default_dct):
    for k, v in default_dct.items():
        if k not in dct:
            dct[k] = v
        elif isinstance(v, dict) and isinstance(dct[k], dict):
            update_dict_with_defaults(dct[k], v)


def print_if(cond, text):
    if cond:
        print(text)
