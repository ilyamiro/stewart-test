from typing import Dict, Any
import yaml
import os
import logging

from source.core.i18n.translator import Translator

log = logging.getLogger("config-loader")

class Loader:
    def __init__(self):
        self.config_data: Dict[str, Any] = {}
        self.config_path: str = ""

    def load(self, config_path: str) -> Dict[str, Any]:
        self.config_path = config_path

        if not os.path.exists(self.config_path):
            log.error(f"Config file not found at {self.config_path}")
            raise FileNotFoundError(f"Config file not found at {self.config_path}")

        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config_data = yaml.safe_load(file) or {}
                log.info(f"Successfully loaded config from {self.config_path}")
        except Exception as e:
            log.error(f"Failed to load config file {self.config_path}: {e}")
            self.config_data = {}
            raise

        return self.config_data

    def initialize_translator(self) -> Translator:
        lang_code = self.get("settings.lang.prefix", "en")
        relative_locales_dir = self.get("settings.lang.locales", "config/lang")

        project_root = os.getcwd()
        lang_dir = os.path.join(project_root, relative_locales_dir)

        translator = Translator(lang_code=lang_code, path=lang_dir)
        log.info(f"Translator initialized with language '{lang_code}' from {lang_dir}")

        return translator

    def get(self, key_path: str, default: Any = None) -> Any:
        keys = key_path.split('.')
        value = self.config_data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value