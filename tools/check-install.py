#!/usr/bin/env python

import importlib
import re
import sys

import six.moves.configparser as configparser


def main():
    errors = 0
    pattern = re.compile(r'^(.*?)\s*=\s*([^:]*?):.*$')
    config = configparser.ConfigParser()
    config.read('setup.cfg')
    console_scripts = config.get('entry_points', 'console_scripts')
    for script in console_scripts.split('\n'):
        match = pattern.match(script)
        if match:
            (script, module) = match.groups()
            try:
                importlib.import_module(module)
            except ImportError as err:
                print('Imports for %s failed:\n\t%s' % (script, err))
                errors += 1
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
