from source.core.config import Loader
from source.core.events import EventBus, Event, Cycle, Payload
import logging

log = logging.getLogger(__name__)


class API:
    def __init__(self):
        self.config = None
        self.loader = Loader()
        self.i18n = self.loader.initialize_translator()

        self.bus = EventBus()

    def load_config(self, path: str) -> None:
        self.config = self.loader.load(path)
        log.info(f"Config loaded from {path}")
