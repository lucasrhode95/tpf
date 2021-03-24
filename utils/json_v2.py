"""
Extends the original JSON lib capabilities
"""
import inspect
import json
import os


def obj_to_dict(o: any) -> dict:
    if isinstance(o, dict):
        return {k: obj_to_dict(v) for k, v in o.items()}
    elif isinstance(o, list):
        return [obj_to_dict(x) for x in o]
    elif hasattr(o, '__dict__'):
        return {k: obj_to_dict(v) for k, v in o.__dict__.items()}

    return o


def dumps(o: any) -> str:
    return json.dumps(obj_to_dict(o), sort_keys=True, indent=3, default=str)


def load(file_path: str, encoding='utf-8', root_dir=None) -> dict:
    if root_dir is None:
        caller_path = os.path.abspath(inspect.stack()[1][0].f_code.co_filename)
        caller_dir = os.path.dirname(caller_path)
        root_dir = caller_dir

    file_path = os.path.join(root_dir, file_path)

    with open(file_path, encoding=encoding) as f:
        return json.load(f)
