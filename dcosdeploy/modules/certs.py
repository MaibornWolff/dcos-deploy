from cryptography.hazmat import backends
from cryptography.hazmat.primitives import serialization
from ..base import ConfigurationException
from ..util.output import echo
from ..adapters.ca import CAAdapter
from ..adapters.secrets import SecretsAdapter


class Cert(object):
    def __init__(self, name, cert_secret, key_secret, dn, hostnames, encoding, format, algorithm, key_size):
        self.name = name
        self.cert_secret = cert_secret
        self.key_secret = key_secret
        self.dn = dn
        self.hostnames = hostnames
        self.encoding = encoding
        self.format = format
        self.algorithm = algorithm
        self.key_size = key_size


def parse_config(name, config, config_helper):
    cert_secret = config.get("cert_secret")
    key_secret = config.get("key_secret")
    dn = config.get("dn")
    hostnames = config.get("hostnames", list())
    encoding = config.get("encoding")
    format = config.get("format")
    algorithm = config.get("algorithm", "rsa").lower()
    key_size = config.get("key_size")
    if not cert_secret:
        raise ConfigurationException("Cert %s has no cert_secret" % name)
    if not key_secret:
        raise ConfigurationException("Cert %s has no key_secret" % name)
    if not dn:
        raise ConfigurationException("Cert %s has no dn" % name)
    if encoding and not encoding.lower() in ("pem", "der"):
        raise ConfigurationException("Cert %s encoding must be one of pem, der" % name)
    if format and not format.lower() in ("pkcs1", "pkcs8"):
        raise ConfigurationException("Cert %s format must be one of pkcs1, pkcs8" % name)
    if not algorithm in ("rsa", "ecdsa"):
        raise ConfigurationException("Cert %s algorithm must be one of rsa, ecdsa" % name)
    if algorithm == "rsa":
        if key_size:
            key_size = int(key_size)
            if not key_size in (2048, 4096, 8192):
                raise ConfigurationException("Cert %s key_size must be one of 2048, 4096, 8192" % name)
        else:
            key_size = 2048
    elif algorithm == "ecdsa":
        if key_size:
            key_size = int(key_size)
            if not key_size in (256, 384, 512):
                raise ConfigurationException("Cert %s key_size must be one of 256, 384, 512" % name)
        else:
            key_size = 256
    cert_secret = config_helper.render(cert_secret)
    key_secret = config_helper.render(key_secret)
    for k, v in dn.items():
        dn[k] = config_helper.render(v)
    hostnames = [config_helper.render(hn) for hn in hostnames]
    return Cert(name, cert_secret, key_secret, dn, hostnames, encoding, format, algorithm, key_size)


class CertsManager(object):
    def __init__(self):
        self.ca = CAAdapter()
        self.secrets = SecretsAdapter()

    def deploy(self, config, dependencies_changed=False, force=False):
        cert_secret = self.secrets.get_secret(config.cert_secret)
        key_secret = self.secrets.get_secret(config.key_secret)
        if key_secret and cert_secret:
            echo("\tSecrets already exist. Not doing anything.")
            return False
        if cert_secret and not key_secret:
            echo("\tDeleting existing secret %s" % config.cert_secret)
            self.secrets.delete_secret(config.cert_secret)
        if not cert_secret and key_secret:
            echo("\tDeleting existing secret %s" % config.key_secret)
            self.secrets.delete_secret(config.key_secret)

        echo("\tGenerating private key")
        csr, private_key = self.ca.generate_key(config.dn, config.hostnames, config.algorithm, config.key_size)
        private_key = _convert_key(config.encoding, config.format, private_key)
        echo("\tSigning csr")
        cert = self.ca.sign_csr(csr, config.hostnames)
        echo("\tCreating secrets")
        self.secrets.write_secret(config.key_secret, file_content=private_key, update=False)
        self.secrets.write_secret(config.cert_secret, file_content=cert, update=False)
        echo("\tFinished")
        return True

    def dry_run(self, config, dependencies_changed=False):
        cert_secret = self.secrets.get_secret(config.cert_secret)
        key_secret = self.secrets.get_secret(config.key_secret)
        if key_secret and cert_secret:
            return False
        elif cert_secret and not key_secret:
            echo("Would delete existing secret %s for cert %s and recreate" % (config.cert_secret, config.name))
            return True
        elif not cert_secret and key_secret:
            echo("Would delete existing secret %s for cert %s and recreate" % (config.key_secret, config.name))
            return True
        else:
            echo("Would create cert %s" % config.name)
            return True

    def delete(self, config, force=False):
        echo("\tDeleting secrets for cert %s" % config.name)
        cert_secret = self.secrets.get_secret(config.cert_secret)
        key_secret = self.secrets.get_secret(config.key_secret)
        if not key_secret and not cert_secret:
            echo("\tSecrets already deleted. Not doing anything.")
            return False
        if cert_secret:
            echo("\tDeleting existing secret %s" % config.cert_secret)
            self.secrets.delete_secret(config.cert_secret)
        if key_secret:
            echo("\tDeleting existing secret %s" % config.key_secret)
            self.secrets.delete_secret(config.key_secret)
        echo("\tDeletion complete.")
        return True

    def dry_delete(self, config):
        cert_secret = self.secrets.get_secret(config.cert_secret)
        key_secret = self.secrets.get_secret(config.key_secret)
        if key_secret or cert_secret:
            echo("Would delete secrets for cert %s" % config.name)
            return True
        else:
            return False


def _convert_key(encoding_name, format_name, private_key):
    if not encoding_name and not format_name:
        return private_key
    backend = backends.default_backend()
    key_obj = serialization.load_pem_private_key(private_key.encode("utf-8"), None, backend)
    if encoding_name.lower() == "pem":
        encoding = serialization.Encoding.PEM
    elif encoding_name.lower() == "der":
        encoding = serialization.Encoding.DER
    else:
        raise Exception("Unknown key encoding: %s" % encoding_name)
    if format_name.lower() == "pkcs1":
        format = serialization.PrivateFormat.TraditionalOpenSSL
    elif format_name.lower() == "pkcs8":
        format = serialization.PrivateFormat.PKCS8
    else:
        raise Exception("Unknown key format: %s" % format_name)

    target_key = key_obj.private_bytes(encoding=encoding, format=format, encryption_algorithm=serialization.NoEncryption())
    return target_key.decode("utf-8")


__config__ = Cert
__manager__ = CertsManager
__config_name__ = "cert"
