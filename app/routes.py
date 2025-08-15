import os
import re
from flask import Blueprint, render_template, request, redirect, url_for, send_file, abort, jsonify
from .helpers import (
    BLOCK_BINARY_EXTS,
    get_recent_folders, add_recent_folder,
    set_last_open_file, get_last_open_file,
    build_tree,
    get_read_files, mark_file_read,
    get_mime_type
)

main_bp = Blueprint("main_bp", __name__)

BASE_DIR = None

@main_bp.route("/")
def index():
    global BASE_DIR
    if not BASE_DIR:
        return render_template("selector.html", recent_folders=get_recent_folders())

    sort_mode = request.args.get("sort", "alpha")
    last_file = get_last_open_file(BASE_DIR)
    read_files = get_read_files(BASE_DIR)

    return render_template(
        "main.html",
        tree=build_tree(BASE_DIR, sort_mode),
        sort_mode=sort_mode,
        last_file=last_file,
        BASE_DIR=BASE_DIR,
        read_files=read_files
    )

@main_bp.route("/use_folder")
def use_folder():
    global BASE_DIR
    folder = request.args.get("folder", "")
    if os.path.isdir(folder):
        BASE_DIR = os.path.abspath(folder)
        add_recent_folder(BASE_DIR)
        return redirect(url_for("main_bp.index"))
    return redirect(url_for("main_bp.index"))

@main_bp.route("/change_folder")
def change_folder():
    return render_template("selector.html", recent_folders=get_recent_folders())

@main_bp.route("/set_folder", methods=["POST"])
def set_folder():
    global BASE_DIR
    folder = (request.form.get("folder") or "").strip()
    if not os.path.isdir(folder):
        return "<h3>Invalid folder. <a href='/change_folder'>Try again</a></h3>"
    BASE_DIR = os.path.abspath(folder)
    add_recent_folder(BASE_DIR)
    return redirect(url_for("main_bp.index"))

@main_bp.route("/view")
def view():
    global BASE_DIR
    if not BASE_DIR:
        return redirect(url_for("main_bp.index"))

    path = request.args.get("path", "")
    abs_path = os.path.abspath(os.path.join(BASE_DIR, path))
    if not abs_path.startswith(BASE_DIR):
        abort(400, "Invalid path")
    if not os.path.exists(abs_path):
        abort(404, "File not found")

    set_last_open_file(BASE_DIR, path)

    size = os.path.getsize(abs_path)
    if size == 0:
        return "<div style='font-family:sans-serif;padding:20px;color:#666;'>This file is empty.</div>"

    ext = os.path.splitext(abs_path)[1].lower()
    mime = get_mime_type(abs_path)

    # Block unsafe binaries
    if ext in BLOCK_BINARY_EXTS:
        return "<div style='padding:20px;color:red;font-family:sans-serif;'>⚠ Cannot preview this file. Download instead.</div>"

    # PDF
    if ext == ".pdf" or mime == "application/pdf":
        return f'<iframe src="/file?path={path}" style="width:100%;height:100%;border:none;"></iframe>'

    # SVG
    if ext == ".svg" or (mime and mime == "image/svg+xml"):
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            return f"<div style='max-width:100%;max-height:100%;'>{svg_content}</div>"
        except Exception:
            return f'<img src="/file?path={path}" style="max-width:100%;max-height:100%;"/>'

    # HTML redirect detection
    if mime and mime.startswith("text/html"):
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                html_content = f.read()
            match = re.search(r'window\.location\s*=\s*"([^"]+)"', html_content)
            if match:
                redirect_url = match.group(1)
                return f"""
                <div style="font-family:sans-serif;padding:20px">
                    <h3>External link detected</h3>
                    <p>This file redirects externally:</p>
                    <a href="{redirect_url}" target="_blank">Open in new tab</a>
                </div>
                """
            return html_content
        except Exception:
            return send_file(abs_path)

    # Images (other than SVG)
    if mime and mime.startswith("image"):
        return f'<img src="/file?path={path}" style="max-width:100%;max-height:100%;display:block;margin:auto"/>'

    # Video / audio
    if mime and (mime.startswith("video") or mime.startswith("audio")):
        return f'<video src="/file?path={path}" controls preload="metadata" style="width:100%;height:100%"></video>'

    # Text-like files
    if (mime and mime.startswith("text")):
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return f"<pre style='padding:10px;background:#111;color:#eee;overflow:auto'>{content}</pre>"
        except Exception:
            return send_file(abs_path)

    # Fallback: unknown type
    return send_file(abs_path)

@main_bp.route("/mark_read", methods=["POST"])
def mark_read_route():
    global BASE_DIR
    data = request.get_json()
    folder = data.get("folder")
    file_path = data.get("file")
    read = data.get("read", False)
    if folder and file_path:
        mark_file_read(folder, file_path, read)
        return jsonify(success=True)
    return jsonify(success=False)

@main_bp.route("/file")
def serve_file():
    global BASE_DIR
    if not BASE_DIR:
        return redirect(url_for("main_bp.index"))
    path = request.args.get("path", "")
    abs_path = os.path.abspath(os.path.join(BASE_DIR, path))
    if not abs_path.startswith(BASE_DIR):
        abort(400, "Invalid path")
    if not os.path.exists(abs_path):
        abort(404, "File not found")
    return send_file(abs_path)
