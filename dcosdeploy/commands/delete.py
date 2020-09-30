import click
from . import maingroup
from ..delete import DeletionRunner
from ..util import detect_yml_file, read_yaml
from ..util.output import echo
from ..util.vars import get_variables


@maingroup.command()
@click.option("--config-file", "-f", help="Path to alternate config file, default is dcos.yml. Can be provided multiple times", required=False, multiple=True)
@click.option("--var", "-e", help="Variable", multiple=True)
@click.option("--only", help="Deploy only specified object")
@click.option("--dry-run", "-d", help="Only check what would be done", is_flag=True)
@click.option("--yes", help="Do deletion without asking", is_flag=True)
def delete(config_file, var, only, dry_run, yes):
    provided_variables = get_variables(var)
    if not config_file:
        config_file = detect_yml_file("dcos")
    runner = DeletionRunner(config_file, provided_variables)
    if only:
        if runner.partial_dry_run(only) and not dry_run:
            if yes or click.confirm("Do you want to apply these changes?", default=False):
                runner.run_partial_deletion(only)
            else:
                echo("Not doing anything")
    else:
        if runner.dry_run() and not dry_run:
            if yes or click.confirm("Do you want to apply these changes?", default=False):
                runner.run_deletion()
            else:
                echo("Not doing anything")
