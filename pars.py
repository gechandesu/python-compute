import re


def _split_unit(val: str) -> dict | None:
    match = re.match(r'([0-9]+)([a-z]+)', val, re.I)
    if match:
        return {
            'value': match.groups()[0],
            'unit': match.groups()[1],
        }
    return None


def _parse_complex_arg(arg: str) -> dict:
    # key=value --> {'key': 'value'}
    if re.match(r'.+=.+', arg):
        key, val = arg.split('=')
    # system --> {'is_system': True}
    # ro --> {'is_readonly': True}
    elif re.match(r'^[a-z0-9_\.\-]+$', arg, re.I):
        key = 'is_' + arg.replace('ro', 'readonly')
        val = True
    else:
        raise ValueError('Invalid argument pattern')
    # key=15GiB --> {'key': {'value': 15, 'unit': 'GiB'}}
    if not isinstance(val, bool):
        val = _split_unit(val) or val
    return {key: val}


print(_parse_complex_arg('source=/volumes/50c4410b-2ef0-4ffd-a2e5-04f0212772d4.qcow2'))
print(_parse_complex_arg('capacity=15GiB'))
print(_parse_complex_arg('system'))
print(_parse_complex_arg('cpu.cores=8'))
