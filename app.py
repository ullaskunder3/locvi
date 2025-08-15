import os
import re
import json
import mimetypes
from datetime import datetime
from flask import Flask, send_file, render_template_string, request, abort, redirect, url_for, jsonify
from appdirs import user_config_dir

PORT = 8080
BASE_DIR = None

TEXT_SAFE_EXTS = {".sh", ".bat", ".cmd", ".ps1", ".py", ".bar", ".torrent"}
BLOCK_BINARY_EXTS = {".exe", ".dll", ".zip", ".rar", ".tar", ".gz", ".7z"}

APP_NAME = "LocVi"
CONFIG_DIR = user_config_dir(APP_NAME)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

app = Flask(__name__)

# ---------- Config helpers ----------
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

# ---------- Last opened files ----------
def set_last_open_file(folder: str, file_path: str):
    cfg = load_config()
    last_files = cfg.get("last_open_file", {})
    last_files[os.path.abspath(folder)] = file_path
    cfg["last_open_file"] = last_files
    save_config(cfg)

def get_last_open_file(folder: str):
    cfg = load_config()
    return cfg.get("last_open_file", {}).get(os.path.abspath(folder))

# ---------- Read-tracking ----------
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

# ---------- Templates ----------
FOLDER_PICKER = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Select Folder</title>
<style>
body { font-family: Arial, sans-serif; background:#f4f4f4; display:flex; align-items:center; justify-content:center; height:100vh; }
#box { background:white; padding:20px; border-radius:8px; box-shadow:0 0 10px rgba(0,0,0,0.2); width: 420px; }
.small { color:#666; font-size:12px; }
</style>
</head>
<body>
<div id="box">
  <h3>Select the folder containing your files</h3>
  {% if recent_folders %}
    <p class="small">Recent folders:</p>
    <ul>
      {% for f in recent_folders %}
        <li><a href="/use_folder?folder={{ f|urlencode }}">{{ f }}</a></li>
      {% endfor %}
    </ul>
    <hr>
  {% endif %}
  <form action="/set_folder" method="post">
    <input type="text" name="folder" placeholder="Enter full path" style="width:100%" required>
    <br><br>
    <button type="submit">Open</button>
  </form>
  <p class="small">Tip: copy & paste the path from your file explorer.</p>
</div>
</body>
</html>
"""

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Course Browser</title>
<style>
body { margin:0; font-family: Arial, sans-serif; display:flex; height:100vh; }
#sidebar { width:320px; background:#f4f4f4; overflow:auto; padding:10px; border-right:1px solid #ccc; }
#content { flex:1; padding:0; display:flex; flex-direction:column; }
iframe, video { flex:1; border:none; }
a { text-decoration:none; display:block; padding:4px; color:#333; }
a:hover { background:#ddd; }
.folder { font-weight:bold; margin-top:8px; }
.topbar { padding:6px 8px; background:#ddd; font-size:14px; display:flex; gap:10px; align-items:center; justify-content:space-between; }
.small { font-size:12px; color:#555; }
.read-checkbox { margin-left:6px; }
</style>
<script>
function toggleRead(folder, file, checkbox) {
console.log("folder file checkbox:", {folder: folder, file: file, read: checkbox.checked})
    fetch('/mark_read', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({folder: folder, file: file, read: checkbox.checked})
    }).then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('State updated successfully');
        } else {
            console.error('Failed to update state');
        }
    });
}
</script>

</head>
<body>
<div id="sidebar">
  <div class="topbar">
    <div>
      Sort
      {% if sort_mode == "alpha" %}<b>Alphabetical</b> | <a href="/?sort=smart">Smart</a>
      {% else %}<a href="/?sort=alpha">Alphabetical</a> | <b>Smart</b>
      {% endif %}
    </div>
    <div><a class="small" href="/change_folder">Change folder--</a></div>
  </div>

  {% for folder, files in tree.items() %}
    {% if folder %}<div class="folder">{{ folder }}</div>{% endif %}
    {% for f in files %}
      {% set rel_path = (folder + '/' + f) if folder else f %}
      <div>
        <a href="/view?path={{ rel_path }}" target="viewer">{{ f }}</a>
<input type="checkbox" class="read-checkbox"
       onchange='toggleRead({{ BASE_DIR|tojson }}, {{ rel_path|tojson }}, this)'
       {% if rel_path in read_files %}checked{% endif %} />
      </div>
    {% endfor %}
  {% endfor %}
</div>

<div id="content">
<iframe name="viewer" src="{{ url_for('view', path=last_file) if last_file else '' }}"></iframe>
</div>
</body>
</html>
"""

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

def build_tree(sort_mode="alpha"):
    tree = {}
    for root, dirs, files in os.walk(BASE_DIR):
        if sort_mode == "smart":
            dirs.sort(key=sort_key)
            files.sort(key=sort_key)
        else:
            dirs.sort()
            files.sort()
        rel_root = os.path.relpath(root, BASE_DIR)
        if rel_root == ".":
            rel_root = ""
        tree[rel_root] = files
    return tree

# ---------- Routes ----------
@app.route("/")
def index():
    global BASE_DIR
    if not BASE_DIR:
        return render_template_string(FOLDER_PICKER, recent_folders=get_recent_folders())
    sort_mode = request.args.get("sort", "alpha")
    last_file = get_last_open_file(BASE_DIR)
    read_files = get_read_files(BASE_DIR)
    return render_template_string(
        TEMPLATE,
        tree=build_tree(sort_mode),
        sort_mode=sort_mode,
        last_file=last_file,
        BASE_DIR=BASE_DIR,
        read_files=read_files
    )

@app.route("/mark_read", methods=["POST"])
def mark_read_route():
    data = request.get_json()
    folder = data.get("folder")
    file_path = data.get("file")
    read = data.get("read", False)
    mark_file_read(folder, file_path, read)
    return jsonify(success=True)

@app.route("/use_folder")
def use_folder():
    global BASE_DIR
    folder = request.args.get("folder", "")
    if os.path.isdir(folder):
        BASE_DIR = os.path.abspath(folder)
        add_recent_folder(BASE_DIR)
        return redirect(url_for("index"))
    return redirect(url_for("index"))

@app.route("/change_folder")
def change_folder():
    return render_template_string(FOLDER_PICKER, recent_folders=get_recent_folders())

@app.route("/set_folder", methods=["POST"])
def set_folder():
    global BASE_DIR
    folder = (request.form.get("folder") or "").strip()
    if not os.path.isdir(folder):
        return "<h3>Invalid folder. <a href='/change_folder'>Try again</a></h3>"
    BASE_DIR = os.path.abspath(folder)
    add_recent_folder(BASE_DIR)
    return redirect(url_for("index"))

@app.route("/view")
def view():
    global BASE_DIR
    if not BASE_DIR:
        return redirect(url_for("index"))
    path = request.args.get("path", "")
    abs_path = os.path.abspath(os.path.join(BASE_DIR, path))
    if not abs_path.startswith(BASE_DIR):
        abort(400, "Invalid path")
    if not os.path.exists(abs_path):
        abort(404, "File not found")
    set_last_open_file(BASE_DIR, path)
    if os.path.getsize(abs_path) == 0:
        return "<div style='font-family:sans-serif;padding:20px;color:#666;'>This file is empty.</div>"
    ext = os.path.splitext(abs_path)[1].lower()
    if ext in BLOCK_BINARY_EXTS:
        return "<div style='padding:20px;color:red;font-family:sans-serif;'>⚠ This file type cannot be opened here. Download instead.</div>"
    if ext in TEXT_SAFE_EXTS:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return f"<pre style='padding:10px;background:#111;color:#eee;overflow:auto'>{content}</pre>"
    mime, _ = mimetypes.guess_type(abs_path)
    if mime and mime.startswith("text/html"):
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()
        match = re.search(r'window\\.location\\s*=\\s*"([^"]+)"', html_content)
        if match:
            redirect_url = match.group(1)
            return f"""
            <div style="font-family:sans-serif;padding:20px">
                <h3>External link detected</h3>
                <p>This site may not allow loading inside this window.</p>
                <p><a href="{redirect_url}" target="_blank">Open in new tab</a></p>
                <iframe src="{redirect_url}" style="width:100%;height:80%;border:none;"></iframe>
            </div>
            """
        return html_content
    elif mime and mime.startswith("video"):
        return f'<video src="/file?path={path}" controls autoplay style="width:100%;height:100%"></video>'
    else:
        return send_file(abs_path)

@app.route("/file")
def serve_file():
    global BASE_DIR
    if not BASE_DIR:
        return redirect(url_for("index"))
    path = request.args.get("path", "")
    abs_path = os.path.abspath(os.path.join(BASE_DIR, path))
    if not abs_path.startswith(BASE_DIR):
        abort(400, "Invalid path")
    if not os.path.exists(abs_path):
        abort(404, "File not found")
    return send_file(abs_path)

if __name__ == "__main__":
    print(f"Open http://localhost:{PORT} in your browser")
    app.run(port=PORT, debug=False)
