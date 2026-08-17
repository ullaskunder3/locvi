import os
import threading
from app import create_app
import webview

app = create_app()

def start_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="127.0.0.1", port=port, threaded=True)

if __name__ == "__main__":
    # Configure Qt WebEngine PDF Viewer settings on Linux before GUI launch
    try:
        from PySide6.QtWebEngineCore import QWebEngineSettings
        settings = QWebEngineSettings.globalSettings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
    except Exception as e:
        print("QtWebEngineSettings notice:", e)

    t = threading.Thread(target=start_flask, daemon=True)
    t.start()

    # Create a native window
    webview.create_window(
        "Local File Explorer",
        "http://127.0.0.1:8080",
        width=1200,
        height=800,
        confirm_close=True,
    )
    webview.start(gui='qt')
