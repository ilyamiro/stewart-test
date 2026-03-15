import logging
import os
from source.logs import setup_logging

from source.core.app import App
from source.api import api

setup_logging()
log = logging.getLogger("ROOT")

def main():
    log.debug(f"Application started. PID: {os.getpid()}")

    app = App(api)

    app.process("Hello")




main()

