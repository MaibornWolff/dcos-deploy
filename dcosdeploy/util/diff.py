import base64
import difflib
import json
from copy import deepcopy
from colorama import Fore, init
from . import global_config


init()

BASE64_ENDINGS = ["base64", "b64", "base_64"]


def _color_diff_line(line):
    if not global_config.color_diffs:
        return line
    if line.startswith('+') and not line.startswith('+++'):
        return Fore.GREEN + line + Fore.RESET
    elif line.startswith('-') and not line.startswith('---'):
        return Fore.RED + line + Fore.RESET
    elif line.startswith('@@'):
        return Fore.BLUE + line + Fore.RESET
    else:
        return line


def _is_base64_key(key):
    for b64_ending in BASE64_ENDINGS:
        if key.lower().endswith(b64_ending):
            return True
    return False


def _base64_decoded_copy(dictionary):
    def _base64_decode_rec(dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                _base64_decode_rec(value)
            if isinstance(value, list):
                for val in value:
                    if isinstance(val, dict):
                        _base64_decode_rec(val)
            if isinstance(value, str) and _is_base64_key(key):
                try:
                    decoded = base64.b64decode(value.encode('utf-8'), validate=True)
                    if decoded != value:
                        dictionary[key] = decoded.decode('utf-8')
                except Exception as e:
                    print("Error while decoding base64 config value in key '%s': %s" % (key, str(e)))

    cp = deepcopy(dictionary)
    _base64_decode_rec(cp)
    return cp


def compare_dicts(left, right):
    left = _base64_decoded_copy(left)
    right = _base64_decoded_copy(right)
    left_str = json.dumps(left, indent=2, sort_keys=True)
    right_str = json.dumps(right, indent=2, sort_keys=True)
    return compare_text(left_str, right_str)


def compare_text(left, right):
    is_binary = False
    if not isinstance(left, str):
        try:
            left = left.decode("utf-8")
        except UnicodeDecodeError:
            is_binary = True
    if not is_binary and not isinstance(right, str):
        try:
            right = right.decode("utf-8")
        except UnicodeDecodeError:
            is_binary = True
    if is_binary:
        if left != right:
            return "    <no diff for binary content>"
        else:
            return None
    left = left.replace(r'\n', '\n')
    right = right.replace(r'\n', '\n')
    diff = list(difflib.unified_diff(left.splitlines(), right.splitlines(), lineterm=''))
    if diff:
        return "    " + '\n    '.join([_color_diff_line(line) for line in diff])
    else:
        return None


def update_dict_with_defaults(dct, default_dct):
    for k, v in default_dct.items():
        if k not in dct:
            dct[k] = v
        elif isinstance(v, dict) and isinstance(dct[k], dict):
            update_dict_with_defaults(dct[k], v)
