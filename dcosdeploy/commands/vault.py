import os
import sys
import click
from . import maingroup
from dcosdeploy import util


@maingroup.group()
def vault():
    pass


@vault.command("generate-key")
def generate_key():
    key = util.generate_key()
    click.echo("Your new key: %s" % key)
    click.echo("Keep this safe.")


@vault.command()
@click.option("--input-file", "-i", help="Path to cleartext file", required=True)
@click.option("--output-file", "-o", help="Path where to write the encrypted file", required=True)
@click.option("--key-file", help="File to read the encryption key from. Either this or --key must be set", required=False)
@click.option("--key", "-k", help="Encyption key. Either this or --key-file or --env must be set", required=False)
@click.option("--env", "-e", help="Environment variable to read encyption key from. Either this or --key-file or --key must be set", required=False)
def encrypt(input_file, output_file, key_file, key, env):
    key = _get_key(key_file, key, env)
    with open(input_file) as input_fileobj:
        input_data = input_fileobj.read()
    output_data = util.encrypt_data(key, input_data)
    with open(output_file, "w") as output_fileobj:
        output_fileobj.write(output_data)


@vault.command()
@click.option("--input-file", "-i", help="Path to encrypted file", required=True)
@click.option("--output-file", "-o", help="Path where to write the decrypted file", required=True)
@click.option("--key-file", help="File to read the encryption key from. Either this or --key must be set", required=False)
@click.option("--key", "-k", help="Encyption key. Either this or --key-file or --env must be set", required=False)
@click.option("--env", "-e", help="Environment variable to read encyption key from. Either this or --key-file or --key must be set", required=False)
def decrypt(input_file, output_file, key_file, key, env):
    key = _get_key(key_file, key, env)
    with open(input_file) as input_fileobj:
        input_data = input_fileobj.read()
    output_data = util.decrypt_data(key, input_data)
    with open(output_file, "w") as output_fileobj:
        output_fileobj.write(output_data)


def _get_key(key_filename, key, env):
    if not key_filename and not key and not env:
        click.echo("Either --key-file, --key or --env must be provided. Aborting.")
        sys.exit(1)
    if key_filename:
        with open(key_filename) as key_file:
            key = key_file.read()
    elif env:
        if env not in os.environ:
            click.echo("%s is not set. Aborting." % env)
        key = os.environ.get(env)
    return key
