import os
import subprocess
import sys
import tempfile
import click
from . import maingroup
from .. import util


_key_options = [
    click.option("--key-file", help="File to read the encryption key from. Either this or --key or --env must be set", required=False),
    click.option("--key", "-k", help="Encyption key. Either this or --key-file or --env must be set", required=False),
    click.option("--env", "-e", help="Environment variable to read encyption key from. Either this or --key-file or --key must be set. If neither is set tries the environment variable DCOS_DEPLOY_ENCRYPTION_KEY", required=False),
]


def _requires_key(func):
    for option in reversed(_key_options):
        func = option(func)
    return func


@maingroup.group()
def vault():
    pass


@vault.command("generate-key")
def generate_key():
    """Generate a new key that can be used to encrypt files"""
    key = util.generate_key()
    click.echo("Your new key: %s" % key)
    click.echo("Keep this safe.")


@vault.command()
@click.option("--input-file", "-i", help="Path to cleartext file", required=False)
@click.option("--output-file", "-o", help="Path where to write the encrypted file", required=False)
@click.option("--file", "-f", help="Path for the file to encrypt. Either this or --input-file and --output-file must be set", required=False)
@_requires_key
def encrypt(input_file, output_file, file, key_file, key, env):
    """Encrypt a file with the provided key"""
    if not file and not (input_file and output_file):
        click.echo("Either --input-file and --output-file or --file must be provided. Aborting.")
        sys.exit(1)
    key = _get_key(key_file, key, env)
    if file:
        file = file.replace(".encrypted", "")
    if not input_file:
        input_file = file
    if not output_file:
        output_file = file+".encrypted"
    with open(input_file, "rb") as input_fileobj:
        input_data = input_fileobj.read()
    output_data = util.encrypt_data(key, input_data)
    with open(output_file, "wb") as output_fileobj:
        output_fileobj.write(output_data)


@vault.command()
@click.option("--input-file", "-i", help="Path to encrypted file", required=False)
@click.option("--output-file", "-o", help="Path where to write the decrypted file", required=False)
@click.option("--file", "-f", help="Path for the file to decrypt. Either this or --input-file and --output-file must be set", required=False)
@_requires_key
def decrypt(input_file, output_file, file, key_file, key, env):
    """Decrypt a dcos-deploy vault file"""
    if not file and not (input_file and output_file):
        click.echo("Either --input-file and --output-file or --file must be provided. Aborting.")
        sys.exit(1)
    key = _get_key(key_file, key, env)
    if file:
        file = file.replace(".encrypted", "")
    if not input_file:
        input_file = file+".encrypted"
    if not output_file:
        output_file = file
    with open(input_file, "rb") as input_fileobj:
        input_data = input_fileobj.read()
    output_data = util.decrypt_data(key, input_data)
    with open(output_file, "wb") as output_fileobj:
        output_fileobj.write(output_data)


@vault.command()
@click.option("--input-file", "-f", "-i", help="Path to encrypted file", required=True)
@_requires_key
def view(input_file, key_file, key, env):
    """Show decrypted content of a vault-encrypted file. Only works with utf-8 printable data (not binary files)"""
    key = _get_key(key_file, key, env)
    with open(input_file, "rb") as input_fileobj:
        input_data = input_fileobj.read()
    output_data = util.decrypt_data(key, input_data)
    if not isinstance(output_data, str):
        output_data = output_data.decode("utf-8")
    print(output_data)


@vault.command()
@click.option("--input-file", "-f", "-i", help="Path to encrypted file", required=True)
@_requires_key
def edit(input_file, key_file, key, env):
    """Edit content of a vault-encrypted file. Uses editor from $EDITOR or vi if not set"""
    key = _get_key(key_file, key, env)
    fd, path = tempfile.mkstemp()
    try:
        with open(input_file, "rb") as input_fileobj:
            encrypted_data = input_fileobj.read()
        decrypted_data = util.decrypt_data(key, encrypted_data)
        os.write(fd, decrypted_data)
        editor = os.environ.get("EDITOR", "vi")
        return_code = subprocess.call([editor, path])
        if return_code == 0:
            with open(path, "rb") as tmp_fileobj:
                edited_data = tmp_fileobj.read()
            if edited_data == decrypted_data:
                click.echo("Data remains unchanged. Not saving.")
                return
            encrypted_data = util.encrypt_data(key, edited_data)
            with open(input_file, "wb") as output_fileobj:
                output_fileobj.write(encrypted_data)
        else:
            click.echo("'%s' exited with error. Aborting." % editor)
            sys.exit(1)
    finally:
        os.remove(path)



def _get_key(key_filename, key, env):
    default_key = os.environ.get("DCOS_DEPLOY_ENCRYPTION_KEY")
    if not key_filename and not key and not env and not default_key:
        click.echo("Either --key-file, --key or --env must be provided. Aborting.")
        sys.exit(1)
    if key_filename:
        with open(key_filename) as key_file:
            key = key_file.read()
    elif key:
        return key
    elif env:
        if env not in os.environ:
            click.echo("%s is not set. Aborting." % env)
        return os.environ.get(env)
    elif default_key:
        return default_key
