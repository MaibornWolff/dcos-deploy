
def run_script(script, entity):
    globals_dict = globals().copy()
    globals_dict["entity"] = entity
    exec(script.replace('\\', '\\\\'), globals_dict, globals_dict)
