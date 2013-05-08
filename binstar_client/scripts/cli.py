'''
Binstar command line utility
'''
from argparse import ArgumentParser
from binstar_client.commands import sub_commands

def main():
    
    
    parser = ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(help='commands')
    for command in sub_commands():
        command.add_parser(subparsers)
    
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    
    return args.main(args)
    
