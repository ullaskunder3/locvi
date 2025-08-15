import os
import json
import re
import mimetypes
from datetime import datetime
from appdirs import user_config_dir

# Constants
APP_NAME = "LocVi"
CONFIG_DIR = user_config_dir(APP_NAME)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

BLOCK_BINARY_EXTS = {
    ".exe", ".dll", ".zip", ".rar", ".tar", ".gz", ".7z",
    ".iso",
    ".msi",
    ".bat",
    ".cmd",
    ".scr",
    ".torrent"
}


def get_mime_type(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or ""

# ---------- Config Helpers ----------
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            return {}
    return {}

def save_config(cfg: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

# ---------- Recent folders ----------
def get_recent_folders():
    cfg = load_config()
    folders = cfg.get("recent_folders", [])
    return [f for f in folders if os.path.isdir(f)]

def add_recent_folder(path: str):
    path = os.path.abspath(path)
    cfg = load_config()
    folders = cfg.get("recent_folders", [])
    if path in folders:
        folders.remove(path)
    folders.insert(0, path)
    cfg["recent_folders"] = folders[:3]
    save_config(cfg)

def set_last_open_file(folder: str, file_path: str):
    cfg = load_config()
    last_files = cfg.get("last_open_file", {})
    last_files[os.path.abspath(folder)] = file_path
    cfg["last_open_file"] = last_files
    save_config(cfg)

def get_last_open_file(folder: str):
    cfg = load_config()
    return cfg.get("last_open_file", {}).get(os.path.abspath(folder))

# ---------- Sorting ----------
def sort_key(name: str):
    m = re.match(r'^(\d+)', name)
    if m:
        return (0, int(m.group(1)), name.lower())
    try:
        date_obj = datetime.strptime(name[:10], "%Y-%m-%d")
        return (1, date_obj, name.lower())
    except Exception:
        pass
    return (2, name.lower())

def build_tree(base_dir, sort_mode="alpha"):
    tree = {}
    for root, dirs, files in os.walk(base_dir):
        if sort_mode == "smart":
            dirs.sort(key=sort_key)
            files.sort(key=sort_key)
        else:
            dirs.sort()
            files.sort()
        rel_root = os.path.relpath(root, base_dir)
        if rel_root == ".":
            rel_root = ""
        tree[rel_root] = files
    return tree

# --------- Reading tracker -----------
def mark_file_read(folder: str, file_path: str, read: bool):
    folder_key = os.path.abspath(folder)
    file_path = file_path.replace("\\", "/")
    cfg = load_config()
    read_files = set(cfg.get("read_files", {}).get(folder_key, []))
    if read:
        read_files.add(file_path)
    else:
        read_files.discard(file_path)
    cfg.setdefault("read_files", {})[folder_key] = sorted(read_files)
    save_config(cfg)

def get_read_files(folder: str):
    cfg = load_config()
    return set(cfg.get("read_files", {}).get(os.path.abspath(folder), []))