from . import commands
from .commands.base import RepoCommand


def main(args=None, exit=True):
    main_cmd = RepoCommand(commands, args)
    main_cmd.run()


if __name__ == '__main__':
    main()
