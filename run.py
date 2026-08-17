import os
import threading
from app import create_app
import webview

app = create_app()

def start_flask():
    port = int(os.environ.get("PORT", 8080))
    # use_reloader=False prevents Werkzeug from trying to register signal handlers outside the main thread
    app.run(host="127.0.0.1", port=port, threaded=True, debug=True, use_reloader=False)

if __name__ == "__main__":
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()

    # Create a native window
    webview.create_window(
        "LocVi",
        "http://127.0.0.1:8080",
        width=1200,
        height=800,
        confirm_close=True,
    )
    webview.start(gui='qt')
