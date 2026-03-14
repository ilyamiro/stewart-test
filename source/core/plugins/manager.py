import os
import sys
import yaml
import importlib.util
import logging

log = logging.getLogger(__name__)

class Plugin:
    def __init__(self, plugin_id, name, version, path):
        self.id = plugin_id
        self.name = name
        self.version = version
        self.path = path


class PluginManager:
    def __init__(self, api):
        self.plugins = {}
        self.api = api

    def _process_manifest(self, manifest, plugin_path):
        plugin_id = manifest.get("id")
        name = manifest.get("name")
        version = manifest.get("version")

        if not plugin_id:
            log.debug("Plugin id is missing in manifest")
            return False

        if "/" not in plugin_id:
            log.debug(f"Plugin id '{plugin_id}' must follow 'namespace/plugin'")
            return False

        if plugin_id in self.plugins:
            log.warning(f"Plugin '{plugin_id}' already loaded")
            return False

        plugin = Plugin(
            plugin_id=plugin_id,
            name=name,
            version=version,
            path=plugin_path
        )
        return plugin

    def _import_plugin(self, directory):
        for root, _, files in os.walk(directory):
            for filename in files:
                if not filename.endswith(".py"):
                    continue

                file_path = os.path.join(root, filename)
                module_name = f"plugin_{hash(file_path)}"

                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec is None or spec.loader is None:
                        log.warning(f"Could not load spec for {file_path}")
                        continue

                    module = importlib.util.module_from_spec(spec)

                    setattr(module, "api", self.api)

                    # Execute the module
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    log.info(f"Loaded plugin module {file_path}")

                except Exception as e:
                    log.warning(f"Failed to load plugin module {file_path}: {e}")

    def load(self, manifest_path):
        plugin_manifest_path = os.path.abspath(manifest_path)

        if not os.path.exists(plugin_manifest_path):
            log.warning(f"Plugin manifest at {plugin_manifest_path} not found. Skipping.")
            return False

        with open(plugin_manifest_path, "r", encoding="utf-8") as file:
            manifest_data = yaml.safe_load(file) or {}
            if not manifest_data:
                log.warning(f"Plugin manifest at {plugin_manifest_path} is empty or corrupted. Skipping.")
                return False

        log.info(f"Successfully loaded plugin manifest at {plugin_manifest_path}")

        plugin = self._process_manifest(manifest_data, plugin_manifest_path)
        if not plugin:
            log.warning(f"Error processing plugin manifest at {plugin_manifest_path}")
            return False

        self.plugins[plugin.id] = plugin

        plugin_dir = os.path.dirname(plugin_manifest_path)
        self._import_plugin(plugin_dir)

        return True

