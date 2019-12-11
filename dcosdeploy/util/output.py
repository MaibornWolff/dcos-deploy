import sys
from . import global_config


def echo(text):
    if not global_config.silent:
        print(text, flush=True)


def echo_error(text):
    sys.stderr.write(text+"\n")
    sys.stderr.flush()


def echo_debug(text):
    if not global_config.silent and global_config.debug:
        print(text, flush=True)


def echo_diff(text, diff):
    if not global_config.silent:
        if global_config.debug:
            print(text + ":")
            print(diff, flush=True)
        else:
            print(text, flush=True)