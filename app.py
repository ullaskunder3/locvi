import os
import re
import mimetypes
from datetime import datetime
from flask import Flask, send_file, render_template_string, request, abort, redirect, url_for
from datetime import datetime

PORT = 8080
BASE_DIR = None
TEXT_SAFE_EXTS = {".sh", ".bat", ".cmd", ".ps1", ".py", ".bar", ".torrent"}
BLOCK_BINARY_EXTS = {".exe", ".dll", ".zip", ".rar", ".tar", ".gz", ".7z"}

app = Flask(__name__)

# HTML for folder picker
FOLDER_PICKER = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Select Course Folder</title>
<style>
body { font-family: Arial, sans-serif; background:#f4f4f4; display:flex; align-items:center; justify-content:center; height:100vh; }
#box { background:white; padding:20px; border-radius:8px; box-shadow:0 0 10px rgba(0,0,0,0.2); }
</style>
</head>
<body>
<div id="box">
    <h3>Select the folder containing your course files</h3>
    <form action="/set_folder" method="post">
        <input type="text" name="folder" placeholder="Enter full path" style="width:300px" required>
        <br><br>
        <button type="submit">Open</button>
    </form>
    <p style="color:#666;font-size:12px;">Tip: Copy & paste the path from your file explorer.</p>
</div>
</body>
</html>
"""

# Course browser template
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Course Browser</title>
<style>
body { margin:0; font-family: Arial, sans-serif; display:flex; height:100vh; }
#sidebar { width:300px; background:#f4f4f4; overflow:auto; padding:10px; border-right:1px solid #ccc; }
#content { flex:1; padding:0; display:flex; flex-direction:column; }
iframe, video { flex:1; border:none; }
a { text-decoration:none; display:block; padding:4px; color:#333; }
a:hover { background:#ddd; }
.folder { font-weight:bold; margin-top:8px; }
</style>
</head>
<body>
<div id="sidebar">
    <div style="padding:5px; background:#ddd; font-size:14px; display: flex; align-items: center">
        Sort:
        {% if sort_mode == "alpha" %}
            <b>Alphabetical</b> | <a href="/?sort=smart">Smart</a>
        {% else %}
            <a href="/?sort=alpha">Alphabetical</a> | <b>Smart</b>
        {% endif %}
    </div>
    {% for folder, files in tree.items() %}
        {% if folder %}<div class="folder">{{ folder }}</div>{% endif %}
        {% for f in files %}
            <a href="/view?path={{ (folder + '/' + f) if folder else f }}" target="viewer">{{ f }}</a>
        {% endfor %}
    {% endfor %}
</div>
<div id="content">
    <iframe name="viewer"></iframe>
</div>
</body>
</html>
"""


def sort_key(name):
    # Try to extract leading number
    m = re.match(r'^(\d+)', name)
    if m:
        return (0, int(m.group(1)), name.lower())
    
    # Try to parse as date YYYY-MM-DD
    try:
        date_obj = datetime.strptime(name[:10], "%Y-%m-%d")
        return (1, date_obj, name.lower())
    except:
        pass
    
    # Fallback to string
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

@app.route("/")
def index():
    if not BASE_DIR:
        return FOLDER_PICKER
    sort_mode = request.args.get("sort", "alpha")
    return render_template_string(TEMPLATE, tree=build_tree(sort_mode), sort_mode=sort_mode)

@app.route("/set_folder", methods=["POST"])
def set_folder():
    global BASE_DIR
    folder = request.form.get("folder", "").strip()
    if not os.path.isdir(folder):
        return "<h3>Invalid folder. <a href='/'>Try again</a></h3>"
    BASE_DIR = os.path.abspath(folder)
    return redirect(url_for("index"))

@app.route("/view")
def view():
    path = request.args.get("path", "")
    abs_path = os.path.abspath(os.path.join(BASE_DIR, path))
    
    # safty checking
    if not abs_path.startswith(BASE_DIR):
        abort(400, "Invalid path")
    if not os.path.exists(abs_path):
        abort(404, "File not found")
    
    if os.path.getsize(abs_path) == 0:
        return "<div style='font-family:sans-serif;padding:20px;color:#666;'>This file is empty.</div>"

    ext = os.path.splitext(abs_path)[1].lower()

        # If it's a binary file we don't want to inline
    if ext in BLOCK_BINARY_EXTS:
        return "<div style='padding:20px;color:red;font-family:sans-serif;'>⚠ This file type cannot be opened here. Download instead.</div>"

    # If it's a safe-text file we want to show as plain text
    if ext in TEXT_SAFE_EXTS:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return f"<pre style='padding:10px;background:#111;color:#eee;overflow:auto'>{content}</pre>"

    mime, _ = mimetypes.guess_type(abs_path)
    if mime and mime.startswith("text/html"):
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()
        match = re.search(r'window\.location\s*=\s*"([^"]+)"', html_content)
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
