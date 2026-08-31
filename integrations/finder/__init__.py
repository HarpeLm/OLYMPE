"""Package Finder — re-export paresseux (compatibilite imports)."""

_EXPORTS = {
    "_mdfind": "_helpers",
    "_resolve_by_name": "_helpers",
    "_find": "_helpers",
    "_dst_from": "_helpers",
    "search_file": "search",
    "search_content": "search",
    "list_folder": "search",
    "list_recent_files": "search",
    "open_file": "open_close",
    "open_folder": "open_close",
    "locate_file": "open_close",
    "_running_apps": "open_close",
    "close_file": "open_close",
    "create_folder": "manage",
    "move_file": "manage",
    "rename_file": "manage",
    "copy_file": "manage",
    "duplicate_file": "manage",
    "delete_file": "delete",
    "empty_trash": "delete",
    "delete_folder": "delete",
    "overwrite_file": "delete",
    "check_file_exists": "info",
    "get_file_info": "info",
    "compress_file": "archive",
    "extract_archive": "archive",
    "_read_tags": "tags",
    "_write_tags": "tags",
    "add_tag": "tags",
    "set_favorite": "tags",
}

def __getattr__(name):
    if name in _EXPORTS:
        import importlib
        m = importlib.import_module(f"integrations.finder.{_EXPORTS[name]}")
        return getattr(m, name)
    raise AttributeError(name)
