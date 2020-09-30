import click
from . import maingroup
from ..deploy import DeploymentRunner
from ..util import detect_yml_file, read_yaml, global_config
from ..util.output import echo
from ..util.vars import get_variables


@maingroup.command()
@click.option("--config-file", "-f", help="Path to alternate config file, default is dcos.yml. Can be provided multiple times", required=False, multiple=True)
@click.option("--var", "-e", help="Variable", multiple=True)
@click.option("--only", help="Deploy only specified object")
@click.option("--dry-run", "-d", help="Only check what would be done", is_flag=True)
@click.option("--yes", help="Do deployment without asking", is_flag=True)
@click.option("--debug", help="Enable debug logging", is_flag=True)
@click.option("--force", help="Forces deployment of entity provided with --only", is_flag=True)
def apply(config_file, var, only, dry_run, yes, debug, force):
    global_config.debug = debug
    provided_variables = get_variables(var)
    if not config_file:
        config_file = detect_yml_file("dcos")
    runner = DeploymentRunner(config_file, provided_variables)
    if only:
        if runner.partial_dry_run(only, force=force) and not dry_run:
            if yes or click.confirm("Do you want to apply these changes?", default=False):
                runner.run_partial_deployment(only, force=force)
            else:
                echo("Not doing anything")
    else:
        if runner.dry_run() and not dry_run:
            if yes or click.confirm("Do you want to apply these changes?", default=False):
                runner.run_deployment(force=force)
            else:
                echo("Not doing anything")
