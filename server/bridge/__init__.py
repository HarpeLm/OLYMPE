"""Package bridge — re-export paresseux (compatibilite imports)."""

_EXPORTS = {
    "Recorder": "_recorder",
    "Handler": "_handlers",
    "get_stt": "_engines",
    "get_tts": "_engines",
    "chat_response": "_engines",
    "speak": "_engines",
}

def __getattr__(name):
    if name in _EXPORTS:
        import importlib
        m = importlib.import_module(f"server.bridge.{_EXPORTS[name]}")
        return getattr(m, name)
    raise AttributeError(name)
