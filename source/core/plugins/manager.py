import os
import sys
import yaml
import importlib.util
import logging

from source.core.events import Cycle, Event

log = logging.getLogger(__name__)

class Plugin:
    def __init__(self, plugin_id, name, version, path, entrypoint, dependencies, api_version):
        self.id = plugin_id
        self.name = name
        self.version = version
        self.path = path
        self.entrypoint = entrypoint
        self.dependencies = dependencies
        self.api_version = api_version

class PluginManager:
    def __init__(self, api):
        self.plugins = {}
        self.api = api

    def _process_manifest(self, manifest, plugin_path):
        plugin_id = manifest.get("id")
        name = manifest.get("name")
        version = manifest.get("version")

        # Pull new safe defaults
        entrypoint = manifest.get("entrypoint", "main.py")
        dependencies = manifest.get("dependencies", [])
        api_version = manifest.get("api_version", "1.0.0")

        if not plugin_id:
            log.error("Plugin id is missing in manifest")
            return False

        if "/" not in plugin_id:
            log.error(f"Plugin id '{plugin_id}' must follow 'namespace/plugin'")
            return False

        if plugin_id in self.plugins:
            log.warning(f"Plugin '{plugin_id}' already loaded")
            return False

        plugin = Plugin(
            plugin_id=plugin_id,
            name=name,
            version=version,
            path=plugin_path,
            entrypoint=entrypoint,
            dependencies=dependencies,
            api_version=api_version
        )
        return plugin

    def _import_plugin(self, plugin_dir, entrypoint):
        """Loads ONLY the specified entrypoint file, ignoring utilities and tests."""
        file_path = os.path.join(plugin_dir, entrypoint)

        if not os.path.exists(file_path):
            log.error(f"Plugin entrypoint not found: {file_path}")
            return False

        module_name = f"plugin_{hash(file_path)}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                log.error(f"Could not load spec for {file_path}")
                return False

            module = importlib.util.module_from_spec(spec)

            setattr(module, "api", self.api)
            setattr(module, "Event", Event)
            setattr(module, "Cycle", Cycle)

            # Execute the module
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            log.info(f"Loaded plugin module {file_path}")
            return True

        except Exception as e:
            log.error(f"Failed to load plugin module {file_path}: {e}")
            return False

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

        # Register the plugin object
        self.plugins[plugin.id] = plugin

        plugin_dir = os.path.dirname(plugin_manifest_path)

        # Execute only the designated entrypoint
        self._import_plugin(plugin_dir, plugin.entrypoint)

        return True