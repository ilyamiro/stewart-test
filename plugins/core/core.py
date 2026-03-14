import logging

log = logging.getLogger(__name__)


def _on_plugin_loaded(plugin_id: str):
    log.info("Plugin loaded event received in core plugin: %s", plugin_id)


def setup(plugin):
    plugin.api.boulder()
    plugin.register_hook("plugin.loaded", _on_plugin_loaded, priority=10)


def teardown():
    # `plugin` is injected by the plugin manager at import/setup time.
    plugin.api.unregister_hooks(plugin.plugin.id)
