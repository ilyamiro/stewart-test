from typing import Dict, Any
import yaml
import os
import logging

log = logging.getLogger("i18n")

class Translator():
    def __init__(self, lang_code: str, path: str):
        self.default_lang_code = "en"
        self.path = path

        self.translations: Dict[str, Any] = {}
        self.load(lang_code)
        
    def load(self, lang_code: str):
        self.lang_code = lang_code
        
        file_path = os.path.join(self.path, f"{lang_code}.yaml")
        if not os.path.exists(file_path):
            log.warning(f"Locale with a language code {lang_code} wasn't found. Check whether {file_path} is correct. Falling back to {self.default_lang_code}")
            file_path = os.path.join(self.path, self.default_lang_code + ".yaml") 

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.translations = yaml.safe_load(file) or {}
                log.info(f"Successfuly loaded language file {file_path}")
        except Exception as e:
            log.error(f"Failed to load language file {file_path}: {e}")
            self.translations = {}
            
    def translate(self, key: str, **kwargs) -> str:
        keys = key.split('.')
        value = self.translations
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                value = None
                break
                
        if value is None or not isinstance(value, str):
            log.warning(f"Translation key '{key}' not found in loaded locale.")
            return key
            
        if kwargs:
            try:
                return value.format(**kwargs)
            except KeyError as e:
                log.warning(f"Missing format variable {e} for translation key '{key}'.")
                return value
                
        return value
