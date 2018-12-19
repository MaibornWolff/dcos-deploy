import hashlib
import os
import yaml
from cryptography.fernet import Fernet


def read_yaml(filename):
    with open(filename) as yaml_file:
        data = yaml_file.read()
    return yaml.load(data)


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


def compare_lists(list_a, list_b, print_differences=False, path=""):
    if len(list_a) != len(list_b):
        if print_differences:
            for key in list_a:
                if key not in list_b:
                    print("%s[]: %s missing in remote" % (path, key))
            for key in list_b:
                if key not in list_a:
                    print("%s[]: %s missing in local" % (path, key))
        return False
    if len(list_a) == 0:
        return True
    equal = True
    if isinstance(list_a[0], list):
        for i in range(0, len(list_a)):
            if not compare_lists(list_a[i], list_b[i], print_differences=print_differences, path=path+"[%d]" % i):
                equal = False
    elif isinstance(list_a[0], dict):
        for i in range(0, len(list_a)):
            if not compare_dicts(list_a[i], list_b[i], print_differences=print_differences, path=path+"[%d]" % i):
                equal = False
    else:
        for i in range(0, len(list_a)):
            if list_a[i] != list_b[i]:
                if print_differences:
                    print("%s[%d]: %s != %s" % (path, i, list_a[i], list_b[i]))
                equal = False
    return equal


def compare_dicts(config_a, config_b, print_differences=False, path=""):
    """Compares to configs parsed from json. Returns true if they are equal"""
    equal = True
    keys_a = config_a.keys()
    keys_b = config_b.keys()
    if sorted(keys_a) != sorted(keys_b):
        if print_differences:
            for key in keys_a:
                if key not in keys_b:
                    print("%s: %s missing in remote" % (path, key))
            for key in keys_b:
                if key not in keys_a:
                    print("%s: %s missing in local" % (path, key))
        equal = False

    for key in keys_a:
        value_a = config_a[key]
        value_b = config_b.get(key, None)
        if value_b is None:
            continue
        if type(value_a) != type(value_b):
            if print_differences:
                print("%s: Types differ for %s" % (path, key))
            equal = False
        if isinstance(value_a, list):
            if not compare_lists(value_a, value_b, print_differences=print_differences, path=path+"/"+key):
                equal = False
        elif isinstance(value_a, dict):
            if not compare_dicts(value_a, value_b, print_differences=print_differences, path=path+"/"+key):
                equal = False
        else:
            if value_a != value_b:
                if print_differences:
                    print("%s/%s: %s != %s" % (path, key, value_a, value_b))
                equal = False
    return equal


def update_dict_with_defaults(dct, default_dct):
    for k, v in default_dct.items():
        if k not in dct:
            dct[k] = v
        elif isinstance(v, dict) and isinstance(dct[k], dict):
            update_dict_with_defaults(dct[k], v)



def print_if(cond, text):
    if cond:
        print(text)
