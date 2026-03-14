from collections import defaultdict
import logging
from typing import Callable, Dict, List, Optional

from source.core.config import Loader

log = logging.getLogger(__name__)


class API:
    def __init__(self):
        self.config = None
        self.imports = None
        self._hooks: Dict[str, List[dict]] = defaultdict(list)

        self.loader = Loader()
        self.i18n = self.loader.initialize_translator()

    def load_config(self, path):
        self.config = self.loader.load(path)
        log.info(f"Imported config to api from {path}")

    def boulder(self):
        print("I AM GROOT")

    def register_hook(
        self,
        event: str,
        callback: Callable,
        owner: Optional[str] = None,
        priority: int = 100,
        once: bool = False,
    ) -> None:
        self._hooks[event].append(
            {
                "callback": callback,
                "owner": owner,
                "priority": priority,
                "once": once,
            }
        )
        self._hooks[event].sort(key=lambda item: item["priority"])
        log.debug(
            "Registered hook for %s (owner=%s priority=%s once=%s)",
            event,
            owner,
            priority,
            once,
        )

    def unregister_hooks(self, owner: str) -> None:
        for event, handlers in self._hooks.items():
            self._hooks[event] = [handler for handler in handlers if handler.get("owner") != owner]

    def emit(self, event: str, **kwargs):
        handlers = list(self._hooks.get(event, []))
        for handler in handlers:
            callback = handler["callback"]
            try:
                callback(**kwargs)
            except Exception as exc:
                log.warning(
                    "Hook failed for event '%s' (owner=%s): %s",
                    event,
                    handler.get("owner"),
                    exc,
                )

            if handler.get("once"):
                try:
                    self._hooks[event].remove(handler)
                except ValueError:
                    pass

    def register(self):
        pass
