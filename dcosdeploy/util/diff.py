import difflib
import json


def compare_dicts(left, right):
    left_str = json.dumps(left, indent=2, sort_keys=True)
    right_str = json.dumps(right, indent=2, sort_keys=True)
    diff = list(difflib.unified_diff(left_str.splitlines(), right_str.splitlines(), lineterm=''))
    if diff:
        return "    " + '\n    '.join(diff)
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
