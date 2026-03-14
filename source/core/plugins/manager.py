import importlib.util
import logging
import os
import sys
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

log = logging.getLogger(__name__)


@dataclass
class Plugin:
    id: str
    name: str
    version: str
    path: str
    description: str = ""
    entrypoints: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    assistant_api: str = "1"
    enabled: bool = True
    module_names: List[str] = field(default_factory=list)


class PluginContext:
    """Capability-oriented context handed to plugins."""

    def __init__(self, api: Any, plugin: Plugin):
        self._api = api
        self.plugin = plugin

    @property
    def api(self) -> Any:
        return self._api

    def require_permission(self, permission: str) -> None:
        if permission not in self.plugin.permissions:
            raise PermissionError(
                f"Plugin '{self.plugin.id}' attempted action requiring permission '{permission}'"
            )

    def register_hook(self, event: str, callback, *, priority: int = 100, once: bool = False):
        self.require_permission("assistant.events")
        return self._api.register_hook(
            event,
            callback,
            owner=self.plugin.id,
            priority=priority,
            once=once,
        )

    def emit(self, event: str, **kwargs):
        self.require_permission("assistant.events")
        return self._api.emit(event, **kwargs)


class PluginManager:
    API_MAJOR = "1"

    def __init__(self, api):
        self.plugins: Dict[str, Plugin] = {}
        self.api = api

    def discover(self, root_dir: str = "plugins") -> List[str]:
        manifest_paths: List[str] = []
        if not os.path.isdir(root_dir):
            return manifest_paths

        for root, _, files in os.walk(root_dir):
            if "manifest.yaml" in files:
                manifest_paths.append(os.path.join(root, "manifest.yaml"))

        return sorted(manifest_paths)

    def _validate_assistant_api(self, requested: str, plugin_id: str) -> bool:
        # Simple major compatibility guard. Expand to semver ranges when needed.
        major = str(requested).split(".")[0]
        if major != self.API_MAJOR:
            log.warning(
                "Plugin '%s' targets assistant_api=%s but host major=%s",
                plugin_id,
                requested,
                self.API_MAJOR,
            )
            return False
        return True

    def _process_manifest(self, manifest: Dict[str, Any], plugin_path: str) -> Optional[Plugin]:
        plugin_id = manifest.get("id")
        name = manifest.get("name")
        version = manifest.get("version")

        if not plugin_id:
            log.debug("Plugin id is missing in manifest")
            return None

        if "/" not in plugin_id:
            log.debug("Plugin id '%s' must follow 'namespace/plugin'", plugin_id)
            return None

        if plugin_id in self.plugins:
            log.warning("Plugin '%s' already loaded", plugin_id)
            return None

        entrypoints = manifest.get("entrypoints") or []
        if not isinstance(entrypoints, list):
            log.warning("Plugin '%s' has invalid entrypoints; expected list", plugin_id)
            return None
        if not entrypoints:
            entrypoints = ["*.py"]

        permissions = manifest.get("permissions", [])
        if not isinstance(permissions, list):
            log.warning("Plugin '%s' has invalid permissions; expected list", plugin_id)
            return None

        depends_on = manifest.get("depends_on", [])
        if not isinstance(depends_on, list):
            log.warning("Plugin '%s' has invalid depends_on; expected list", plugin_id)
            return None

        assistant_api = str(manifest.get("assistant_api", self.API_MAJOR))
        enabled = bool(manifest.get("enabled", True))

        plugin = Plugin(
            id=plugin_id,
            name=name or plugin_id,
            version=version or "0.0.0",
            path=plugin_path,
            description=manifest.get("description", ""),
            entrypoints=entrypoints,
            permissions=permissions,
            depends_on=depends_on,
            assistant_api=assistant_api,
            enabled=enabled,
        )
        return plugin

    def _import_module(self, module_name: str, file_path: str) -> Optional[ModuleType]:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            log.warning("Could not load spec for %s", file_path)
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _setup_plugin_module(self, module: ModuleType, context: PluginContext):
        setattr(module, "api", context.api)
        setattr(module, "plugin", context)

        setup_func = getattr(module, "setup", None)
        if callable(setup_func):
            setup_func(context)

    def _iter_entrypoint_files(self, plugin_dir: str, patterns: List[str]) -> List[str]:
        files: List[str] = []
        for pattern in patterns:
            if pattern == "*.py":
                for root, _, filenames in os.walk(plugin_dir):
                    for filename in filenames:
                        if filename.endswith(".py"):
                            files.append(os.path.join(root, filename))
            else:
                candidate = os.path.join(plugin_dir, pattern)
                if os.path.isfile(candidate):
                    files.append(candidate)
                else:
                    log.warning("Entrypoint %s does not exist for plugin dir %s", pattern, plugin_dir)

        return sorted(set(files))

    def _import_plugin(self, plugin: Plugin):
        plugin_dir = os.path.dirname(plugin.path)
        context = PluginContext(self.api, plugin)

        for file_path in self._iter_entrypoint_files(plugin_dir, plugin.entrypoints):
            module_name = f"plugin_{plugin.id.replace('/', '_')}_{hash(file_path)}"

            try:
                module = self._import_module(module_name, file_path)
                if module is None:
                    continue

                self._setup_plugin_module(module, context)
                plugin.module_names.append(module_name)
                log.info("Loaded plugin module %s for %s", file_path, plugin.id)
            except Exception as exc:
                log.warning("Failed to load plugin module %s: %s", file_path, exc)

    def _parse_manifest(self, manifest_path: str) -> Optional[Plugin]:
        with open(manifest_path, "r", encoding="utf-8") as file:
            manifest_data = yaml.safe_load(file) or {}
            if not manifest_data:
                log.warning("Plugin manifest at %s is empty or corrupted. Skipping.", manifest_path)
                return None

        return self._process_manifest(manifest_data, manifest_path)

    def _build_load_order(self, candidates: Dict[str, Plugin]) -> List[Plugin]:
        ordered: List[Plugin] = []
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def visit(plugin_id: str):
            if plugin_id in visited:
                return
            if plugin_id in visiting:
                raise RuntimeError(f"Cycle detected in plugin dependencies at {plugin_id}")

            visiting.add(plugin_id)
            plugin = candidates[plugin_id]
            for dep in plugin.depends_on:
                if dep in candidates:
                    visit(dep)
                elif dep not in self.plugins:
                    raise RuntimeError(f"Plugin '{plugin_id}' depends on missing plugin '{dep}'")

            visiting.remove(plugin_id)
            visited.add(plugin_id)
            ordered.append(plugin)

        for plugin_id in sorted(candidates.keys()):
            visit(plugin_id)

        return ordered

    def load(self, manifest_path: str) -> bool:
        plugin_manifest_path = os.path.abspath(manifest_path)

        if not os.path.exists(plugin_manifest_path):
            log.warning("Plugin manifest at %s not found. Skipping.", plugin_manifest_path)
            return False

        plugin = self._parse_manifest(plugin_manifest_path)
        if plugin is None:
            log.warning("Error processing plugin manifest at %s", plugin_manifest_path)
            return False

        if not plugin.enabled:
            log.info("Plugin '%s' is disabled in manifest", plugin.id)
            return False

        if not self._validate_assistant_api(plugin.assistant_api, plugin.id):
            return False

        self.plugins[plugin.id] = plugin
        self._import_plugin(plugin)
        self.api.emit("plugin.loaded", plugin_id=plugin.id)

        return True

    def load_all(self, root_dir: str = "plugins") -> Tuple[List[str], List[str]]:
        candidates: Dict[str, Plugin] = {}
        for manifest_path in self.discover(root_dir):
            plugin = self._parse_manifest(os.path.abspath(manifest_path))
            if plugin is None:
                continue
            if not plugin.enabled:
                log.info("Plugin '%s' is disabled in manifest", plugin.id)
                continue
            if not self._validate_assistant_api(plugin.assistant_api, plugin.id):
                continue
            candidates[plugin.id] = plugin

        loaded: List[str] = []
        failed: List[str] = []

        try:
            ordered_plugins = self._build_load_order(candidates)
        except RuntimeError as exc:
            log.warning("Unable to build plugin load order: %s", exc)
            return loaded, sorted(candidates.keys())

        for plugin in ordered_plugins:
            if plugin.id in self.plugins:
                failed.append(plugin.id)
                continue

            try:
                self.plugins[plugin.id] = plugin
                self._import_plugin(plugin)
                self.api.emit("plugin.loaded", plugin_id=plugin.id)
                loaded.append(plugin.id)
            except Exception as exc:
                log.warning("Plugin '%s' failed during load: %s", plugin.id, exc)
                failed.append(plugin.id)

        return loaded, failed

    def shutdown(self):
        for plugin in self.plugins.values():
            for module_name in plugin.module_names:
                module = sys.modules.get(module_name)
                teardown = getattr(module, "teardown", None) if module else None
                if callable(teardown):
                    try:
                        teardown()
                    except Exception as exc:
                        log.warning("Teardown failed for plugin '%s' module '%s': %s", plugin.id, module_name, exc)
