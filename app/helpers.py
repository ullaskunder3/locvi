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

# ---------- Pinned & Recent folders ----------
def get_pinned_folders():
    cfg = load_config()
    folders = cfg.get("pinned_folders", [])
    return [f for f in folders if os.path.isdir(f)]

def toggle_pin_folder(path: str) -> bool:
    path = os.path.abspath(path)
    cfg = load_config()
    pinned = cfg.get("pinned_folders", [])
    if path in pinned:
        pinned.remove(path)
        is_pinned = False
    else:
        pinned.append(path)
        is_pinned = True
    cfg["pinned_folders"] = pinned
    save_config(cfg)
    return is_pinned

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
    cfg["recent_folders"] = folders[:5]
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

def set_pdf_page_position(folder: str, file_path: str, page_num: int):
    cfg = load_config()
    positions = cfg.get("pdf_positions", {})
    key = f"{os.path.abspath(folder)}::{file_path}"
    positions[key] = page_num
    cfg["pdf_positions"] = positions
    save_config(cfg)

def get_pdf_page_position(folder: str, file_path: str) -> int:
    cfg = load_config()
    positions = cfg.get("pdf_positions", {})
    key = f"{os.path.abspath(folder)}::{file_path}"
    return positions.get(key, 0)

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
    folder_key = os.path.abspath(folder).replace("\\", "/")
    file_path = file_path.replace("\\", "/")
    cfg = load_config()
    read_files = set(cfg.get("read_files", {}).get(folder_key, []))
    if read:
        read_files.add(file_path)
    else:
        read_files.discard(file_path)
    cfg.setdefault("read_files", {})[folder_key] = sorted(read_files) 
    save_config(cfg)
    log_daily_activity(folder_key, file_path, "completed" if read else "uncompleted")

def get_read_files(folder: str):
    folder_key = os.path.abspath(folder).replace("\\", "/")   # normalize folder
    cfg = load_config()
    stored = cfg.get("read_files", {}).get(folder_key, [])
    return set(p.replace("\\", "/") for p in stored)          # normalize stored file paths

def log_daily_activity(folder: str, file_path: str, action: str):
    cfg = load_config()
    activity = cfg.get("daily_activity", {})
    today = datetime.now().strftime("%Y-%m-%d")
    today_log = activity.get(today, [])
    entry = {
        "time": datetime.now().strftime("%H:%M"),
        "folder": folder,
        "file": file_path,
        "action": action
    }
    today_log.insert(0, entry)
    activity[today] = today_log[:15]
    cfg["daily_activity"] = activity
    save_config(cfg)

def get_dashboard_stats():
    cfg = load_config()
    read_map = cfg.get("read_files", {})
    last_files = cfg.get("last_open_file", {})
    activity_map = cfg.get("daily_activity", {})
    
    total_completed = sum(len(files) for files in read_map.values())
    
    # Calculate progress for recent/pinned workspaces
    workspaces_progress = {}
    for folder in get_recent_folders() + get_pinned_folders():
        folder_key = os.path.abspath(folder).replace("\\", "/")
        if folder_key in workspaces_progress:
            continue
        try:
            tree = build_tree(folder_key)
            all_files = [f for files in tree.values() for f in files]
            total = len(all_files)
            completed_set = get_read_files(folder_key)
            done_count = len([f for f in all_files if f in completed_set or any(f.endswith(x) for x in completed_set)])
            last_file = last_files.get(folder_key) or last_files.get(folder)
            workspaces_progress[folder_key] = {
                "folder": folder_key,
                "name": os.path.basename(folder_key) or folder_key,
                "total": total,
                "completed": min(done_count, total),
                "percent": int((min(done_count, total) / total * 100)) if total > 0 else 0,
                "last_file": last_file
            }
        except Exception:
            pass

    return {
        "total_completed": total_completed,
        "workspaces": workspaces_progress,
        "daily_activity": activity_map
    }
