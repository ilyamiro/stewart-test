from source.core.config import Loader
import logging

log = logging.getLogger(__name__)

class API():
    def __init__(self):
        self.config = None
        self.imports = None

        self.loader = Loader()
        self.i18n = self.loader.initialize_translator()

    def load_config(self, path):
        self.config = self.loader.load(path)
        log.info(f"Imported config to api from {path}")

    def boulder(self):
        print("I AM GROOT")


    def register(self):
        pass
