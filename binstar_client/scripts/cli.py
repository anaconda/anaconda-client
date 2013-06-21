'''
Binstar command line utility
'''
from argparse import ArgumentParser
from binstar_client.commands import sub_commands
from binstar_client import BinstarError
import sys

def main():
    
    
    parser = ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(help='commands')
    for command in sub_commands():
        command.add_parser(subparsers)
    
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    
    try:
        return args.main(args)
    except BinstarError as err:
        sys.stderr.write('%s: %s\n' %(type(err).__name__, err.args[0]))
        raise SystemExit(-1)