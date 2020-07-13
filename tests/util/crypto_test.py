import io
import unittest
from unittest import mock
from dcosdeploy.util import crypto


CRYPTO_KEY = "HRP9xc3i2-3wdJrapc1ckooVO1F7KW4K5eAz5vns--o="
FOOBAR = "foobar"
FOOBAR_MD5_HASH = "3858f62230ac3c915f300c664312c63f"


class CryptoTest(unittest.TestCase):
    def test_encrypt_data(self):
        # str data
        encrypted_data = crypto.encrypt_data(CRYPTO_KEY, FOOBAR)
        decrypted_data = crypto.decrypt_data(CRYPTO_KEY, encrypted_data)
        self.assertEqual(FOOBAR, decrypted_data)
        # bytes data
        encrypted_data = crypto.encrypt_data(CRYPTO_KEY, FOOBAR.encode("utf-8"))
        decrypted_data = crypto.decrypt_data(CRYPTO_KEY, encrypted_data)
        self.assertEqual(FOOBAR.encode("utf-8"), decrypted_data)

    def test_md5_hash_file(self):
        cleartext_data = FOOBAR.encode("utf-8")
        open_mock = mock.mock_open(read_data=cleartext_data)
        with mock.patch('builtins.open', open_mock):
            calculated_hash = crypto.md5_hash_file("testfile")
        self.assertEqual(FOOBAR_MD5_HASH, calculated_hash)

    def test_md5_hash_file_object(self):
        file_object = io.BytesIO(FOOBAR.encode("utf-8"))
        calculated_hash = crypto.md5_hash_file_object(file_object)
        self.assertEqual(FOOBAR_MD5_HASH, calculated_hash)

    def test_md5_hash_str(self):
        # str data
        calculated_hash = crypto.md5_hash_str(FOOBAR)
        self.assertEqual(FOOBAR_MD5_HASH, calculated_hash)
        # bytes data
        calculated_hash = crypto.md5_hash_str(FOOBAR.encode("utf-8"))
        self.assertEqual(FOOBAR_MD5_HASH, calculated_hash)