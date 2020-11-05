import click
from . import maingroup
from .. import __version__


@maingroup.command()
def version():
    """Print the version of dcos-deploy"""
    click.echo(__version__)
