import base64
import difflib
import json
from copy import deepcopy

from colorama import Fore, init

init()

BASE64_ENDINGS = ["base64", "b64", "base_64"]


def color_diff_line(line):
    if line.startswith('+') and not line.startswith('+++'):
        return Fore.GREEN + line + Fore.RESET
    elif line.startswith('-') and not line.startswith('---'):
        return Fore.RED + line + Fore.RESET
    elif line.startswith('@@'):
        return Fore.BLUE + line + Fore.RESET
    else:
        return line


def is_base64_key(key):
    for b64_ending in BASE64_ENDINGS:
        if key.lower().endswith(b64_ending):
            return True
    return False


def base64_decoded_copy(dictionary):
    def _base64_decode_rec(dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                _base64_decode_rec(value)
            if isinstance(value, list):
                for val in value:
                    if isinstance(val, dict):
                        _base64_decode_rec(val)
            if isinstance(value, str) and is_base64_key(key):
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
    left = base64_decoded_copy(left)
    right = base64_decoded_copy(right)
    left_str = json.dumps(left, indent=2, sort_keys=True).replace(r'\n', '\n')
    right_str = json.dumps(right, indent=2, sort_keys=True).replace(r'\n', '\n')
    diff = list(difflib.unified_diff(left_str.splitlines(), right_str.splitlines(), lineterm=''))
    colored_diff = [color_diff_line(line) for line in diff]
    if diff:
        return "    " + '\n    '.join(colored_diff)
    else:
        return None


def compare_text(left, right):
    if not isinstance(left, str):
        left = left.decode("utf-8")
    if not isinstance(right, str):
        right = right.decode("utf-8")
    diff = list(difflib.unified_diff(left.splitlines(), right.splitlines(), lineterm=''))
    if diff:
        return "    " + '\n    '.join(diff)
    else:
        return None


def update_dict_with_defaults(dct, default_dct):
    for k, v in default_dct.items():
        if k not in dct:
            dct[k] = v
        elif isinstance(v, dict) and isinstance(dct[k], dict):
            update_dict_with_defaults(dct[k], v)
