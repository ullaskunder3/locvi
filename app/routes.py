import os
import re
from flask import Blueprint, render_template, request, redirect, url_for, send_file, abort, jsonify
from .helpers import (
    BLOCK_BINARY_EXTS,
    get_recent_folders, add_recent_folder,
    get_pinned_folders, toggle_pin_folder,
    set_last_open_file, get_last_open_file,
    set_pdf_page_position, get_pdf_page_position,
    get_dashboard_stats,
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
            pinned_folders=pinned_folders,
            stats=get_dashboard_stats()
        )

    sort_mode = request.args.get("sort", "alpha")
    tree = build_tree(BASE_DIR, sort_mode)
    last_file = get_last_open_file(BASE_DIR)
    
    # Verify last_file actually exists in the current tree/folder
    if last_file:
        full_last = os.path.abspath(os.path.join(BASE_DIR, last_file))
        if not os.path.exists(full_last):
            last_file = None

    read_files = get_read_files(BASE_DIR)
    is_pinned = BASE_DIR in pinned_folders

    return render_template(
        "main.html",
        tree=tree,
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
        pinned_folders=get_pinned_folders(),
        stats=get_dashboard_stats()
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

    if ext == ".pdf" or mime == "application/pdf":
        import urllib.parse
        last_page = get_pdf_page_position(BASE_DIR, path)
        pdfjs_url = url_for('static', filename='pdfjs/web/viewer.html')
        file_url = url_for('main_bp.serve_file', path=path)
        encoded_file_url = urllib.parse.quote(file_url)
        
        # PDF.js uses 1-based page numbers
        page_hash = f"#page={last_page + 1}&pagemode=none" if last_page >= 0 else "#pagemode=none"
        viewer_src = f"{pdfjs_url}?file={encoded_file_url}{page_hash}"
        
        return f'''
        <iframe id="pdfjs-iframe" src="{viewer_src}" style="width:100%;height:100%;border:none;display:block;"></iframe>
        <script>
            const iframe = document.getElementById('pdfjs-iframe');
            iframe.onload = function() {{
                const pdfWindow = iframe.contentWindow;
                const pdfDoc = pdfWindow.document;

                // 1. Hide the default PDF.js toolbar and make the viewer full screen
                const style = pdfDoc.createElement('style');
                style.textContent = `
                    .toolbar {{ display: none !important; }}
                    #viewerContainer {{ top: 0 !important; height: 100% !important; }}
                    
                    /* Custom popup menu styling */
                    #locvi-popup {{
                        position: fixed;
                        background: #111;
                        color: #fff;
                        padding: 6px;
                        border-radius: 6px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                        display: none;
                        z-index: 99999;
                        font-family: sans-serif;
                        font-size: 13px;
                        gap: 4px;
                    }}
                    #locvi-popup button {{
                        background: transparent;
                        border: none;
                        color: #fff;
                        cursor: pointer;
                        padding: 4px 8px;
                        border-radius: 4px;
                    }}
                    #locvi-popup button:hover {{ background: #333; }}
                `;
                pdfDoc.head.appendChild(style);

                // 2. Create the custom popup menu
                const popup = pdfDoc.createElement('div');
                popup.id = 'locvi-popup';
                popup.innerHTML = `
                    <button id="btn-highlight" title="Highlight">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                    </button>
                    <button id="btn-underline" title="Underline">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3v7a6 6 0 0 0 6 6 6 6 0 0 0 6-6V3"></path><line x1="4" y1="21" x2="20" y2="21"></line></svg>
                    </button>
                    <button id="btn-note" title="Add Note">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                    </button>
                `;
                pdfDoc.body.appendChild(popup);

                // 3. Listen for text selection to show the popup
                pdfDoc.addEventListener('mouseup', function(e) {{
                    const selection = pdfWindow.getSelection();
                    if (selection && !selection.isCollapsed && selection.toString().trim().length > 0) {{
                        popup.style.display = 'flex';
                        popup.style.left = e.clientX + 'px';
                        popup.style.top = (e.clientY - 40) + 'px'; // Show slightly above mouse
                    }} else {{
                        if (e.target.closest('#locvi-popup') == null) {{
                            popup.style.display = 'none';
                        }}
                    }}
                }});

                popup.querySelector('#btn-highlight').addEventListener('click', () => {{
                    alert("Highlight tool clicked! (Backend integration coming next)");
                    popup.style.display = 'none';
                }});

                // Wait for PDFViewerApplication to be ready to track pages
                const checkReady = setInterval(() => {{
                    if (pdfWindow && pdfWindow.PDFViewerApplication && pdfWindow.PDFViewerApplication.eventBus) {{
                        clearInterval(checkReady);
                        pdfWindow.PDFViewerApplication.eventBus.on('pagechanging', function(evt) {{
                            const pageNum = evt.pageNumber - 1; // 0-based for our backend
                            fetch('/save_pdf_page', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{ file: "{path}", page: pageNum }})
                            }}).catch(e => console.error(e));
                        }});
                    }}
                }}, 500);
            }};
        </script>
        '''

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

@main_bp.route("/save_pdf_page", methods=["POST"])
def save_pdf_page():
    global BASE_DIR
    if not BASE_DIR:
        return jsonify(success=False)
    data = request.get_json() or {}
    file_path = data.get("file")
    page_num = data.get("page", 0)
    if file_path:
        set_pdf_page_position(BASE_DIR, file_path, page_num)
        return jsonify(success=True)
    return jsonify(success=False)
