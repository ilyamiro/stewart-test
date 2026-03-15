from source.core.config import Loader
from source.core.events import Cycle
from source.core.plugins import PluginManager
from source.api.api import Event # Importing the new Event class
import logging
import time
from typing import List
from source.core.events import Cycle

log = logging.getLogger(__name__)

def test(payload):
    print("TEST EVENT")
    payload.data["key1"] = "lol"

class App():
    def __init__(self, api):
        self.api = api
        self._check_api_config()

        self._add_cycles([Cycle("app.start", [Event(test, 50, "event_test")])])

        self.pluginm = PluginManager(self.api)
        self.pluginm.load("plugins/core/manifest.yaml")

        payload = self.api.bus.run()
        print(payload)


    def _check_api_config(self, default: str = "config/config.yaml") -> None:
        """
        Checks whether the config was loaded by any of the plugins. Falls back to the default path
        :param default: the fallback config path
        """
        if self.api.config is None:
            log.debug(f"API did not provide a config. Falling back to {default}")
            self.api.load_config(default)

    def _add_cycles(self, cycles: List[Cycle] = []):
        for cycle in cycles:
            self.api.bus.add_cycle(cycle)

    def process(self, text):
        try:
            while True:
                time.sleep(1)
                print("running")
        except KeyboardInterrupt:
            log.info("Shutting down...")
