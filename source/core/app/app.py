from source.core.config import Loader
from source.core.plugins import PluginManager
import logging
import time

log = logging.getLogger(__name__)

class App():
    def __init__(self, api):
        self.api = api
        self._check_api_config()

        self.pluginm = PluginManager(self.api)
        self.pluginm.load("plugins/core/manifest.yaml")

    def _check_api_config(self, default: str = "config/config.yaml") -> None:
        """
        Checks whether the config was loaded by any of the plugins. Falls back to the default path
        :param default: the fallback config path
        """
        if self.api.config is None:
            log.debug(f"API did not provide a config. Falling back to {default}")
            self.api.load_config(default)


    def process(self, text): # placeholder
        while True:
            time.sleep(1)
            print(text)


