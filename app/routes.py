import os
import re
from flask import Blueprint, render_template, request, redirect, url_for, send_file, abort, jsonify
from .helpers import (
    BLOCK_BINARY_EXTS,
    get_recent_folders, add_recent_folder,
    get_pinned_folders, toggle_pin_folder,
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
    pinned_folders = get_pinned_folders()
    if not BASE_DIR:
        return render_template(
            "selector.html",
            recent_folders=get_recent_folders(),
            pinned_folders=pinned_folders
        )

    sort_mode = request.args.get("sort", "alpha")
    last_file = get_last_open_file(BASE_DIR)
    read_files = get_read_files(BASE_DIR)
    is_pinned = BASE_DIR in pinned_folders

    return render_template(
        "main.html",
        tree=build_tree(BASE_DIR, sort_mode),
        sort_mode=sort_mode,
        last_file=last_file,
        BASE_DIR=BASE_DIR,
        read_files=read_files,
        is_pinned=is_pinned,
        pinned_folders=pinned_folders
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
    return render_template(
        "selector.html",
        recent_folders=get_recent_folders(),
        pinned_folders=get_pinned_folders()
    )

@main_bp.route("/browse_folder", methods=["POST"])
def browse_folder():
    global BASE_DIR
    try:
        import webview
        if webview.windows:
            window = webview.windows[0]
            selected = window.create_file_dialog(webview.FOLDER_DIALOG)
            if selected and len(selected) > 0 and os.path.isdir(selected[0]):
                BASE_DIR = os.path.abspath(selected[0])
                add_recent_folder(BASE_DIR)
                return jsonify({"success": True, "folder": BASE_DIR})
    except Exception as e:
        pass
    return jsonify({"success": False, "message": "Could not open native folder picker."})

@main_bp.route("/toggle_pin", methods=["POST"])
def toggle_pin():
    data = request.json or {}
    folder = data.get("folder")
    if folder and os.path.isdir(folder):
        is_pinned = toggle_pin_folder(folder)
        return jsonify({"success": True, "is_pinned": is_pinned})
    return jsonify({"success": False}), 400

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

    # PDF Rendering (Instant Lazy Loading via QtPdf)
    if ext == ".pdf" or mime == "application/pdf":
        try:
            from PySide6.QtPdf import QPdfDocument
            doc = QPdfDocument()
            doc.load(abs_path)
            total_pages = doc.pageCount()
            doc.close()

            if total_pages > 0:
                pages_imgs = []
                for p in range(total_pages):
                    pages_imgs.append(f'''
                    <div style="text-align:center;margin:16px 0;">
                        <img data-src="/pdf_page?path={path}&page={p}" 
                             src="data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'600\' height=\'800\'><rect width=\'100%\' height=\'100%\' fill=\'%231e1e1e\'/><text x=\'50%\' y=\'50%\' fill=\'%23888\' font-size=\'20\' text-anchor=\'middle\'>Loading Page {p+1}...</text></svg>"
                             class="lazy-pdf-page" 
                             style="width:90%;max-width:950px;min-height:400px;box-shadow:0 4px 12px rgba(0,0,0,0.4);border-radius:4px;display:block;margin:auto;" />
                        <div style="color:#aaa;font-size:12px;margin-top:6px;font-family:sans-serif;">Page {p+1} of {total_pages}</div>
                    </div>
                    ''')

                pages_html = "".join(pages_imgs)
                return f'''
                <div id="pdfContainer" style="background:#e0e0e0;height:100vh;overflow-y:auto;padding:20px 0;box-sizing:border-box;">
                    {pages_html}
                </div>
                <script>
                    const observer = new IntersectionObserver((entries) => {{
                        entries.forEach(entry => {{
                            if (entry.isIntersecting) {{
                                const img = entry.target;
                                if (img.dataset.src) {{
                                    img.src = img.dataset.src;
                                    delete img.dataset.src;
                                }}
                                observer.unobserve(img);
                            }}
                        }});
                    }}, {{ rootMargin: "300px 0px" }});

                    document.querySelectorAll(".lazy-pdf-page").forEach(img => observer.observe(img));
                </script>
                '''
        except Exception as e:
            print("QtPdf setup error:", e)

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

@main_bp.route("/pdf_page")
def serve_pdf_page():
    global BASE_DIR
    if not BASE_DIR:
        abort(400, "No workspace folder selected")
    path = request.args.get("path", "")
    page_num = int(request.args.get("page", 0))
    abs_path = os.path.abspath(os.path.join(BASE_DIR, path))

    if not abs_path.startswith(BASE_DIR) or not os.path.exists(abs_path):
        abort(404, "PDF file not found")

    try:
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtCore import QSize, QBuffer, QIODevice
        import io

        doc = QPdfDocument()
        doc.load(abs_path)
        if 0 <= page_num < doc.pageCount():
            page_size = doc.pagePointSize(page_num)
            width = int(page_size.width() * 1.5)
            height = int(page_size.height() * 1.5)
            img = doc.render(page_num, QSize(width, height))
            doc.close()

            # Ensure pure white background behind PDF page rendering (prevent transparency blending)
            from PySide6.QtGui import QImage, QPainter, QColor
            canvas = QImage(img.size(), QImage.Format_ARGB32)
            canvas.fill(QColor(255, 255, 255))
            painter = QPainter(canvas)
            painter.drawImage(0, 0, img)
            painter.end()

            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            canvas.save(buffer, "PNG")
            img_bytes = buffer.data().data()
            buffer.close()

            return send_file(
                io.BytesIO(img_bytes),
                mimetype="image/png"
            )
        doc.close()
    except Exception as e:
        print("Error serving PDF page:", e)

    abort(500, "Error rendering page")
