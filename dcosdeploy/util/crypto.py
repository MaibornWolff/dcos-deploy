import hashlib
from cryptography.fernet import Fernet


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


def md5_hash_file(filename):
    with open(filename, "rb") as source_file:
        return md5_hash_file_object(source_file)


def md5_hash_file_object(file_obj):
    hash_md5 = hashlib.md5()
    for chunk in iter(lambda: file_obj.read(512*1024), b""):
        hash_md5.update(chunk)
    return hash_md5.hexdigest()


def md5_hash_str(string_data):
    if isinstance(string_data, str):
        string_data = string_data.encode("utf-8")
    hash_md5 = hashlib.md5()
    hash_md5.update(string_data)
    return hash_md5.hexdigest()