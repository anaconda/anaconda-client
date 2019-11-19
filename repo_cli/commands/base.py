from ..utils.api import RepoApi
from ..utils.config import store_token, get_config, load_token, DEFAULT_URL


class RepoCommand:
    def __init__(self, config):
        self.config = config
        self.url = config.get('url', DEFAULT_URL)
        self.api = RepoApi(base_url=self.url)

    def register_subcommand(self, subcommand):
        pass


class SubCommand:
    def __init__(self, parent, args):
        self.parent = parent
        self.args = args

    @property
    def api(self):
        return self.parent.api

