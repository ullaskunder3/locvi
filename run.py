import os
from app import create_app

app = create_app()
# for development debug
# app.config["DEBUG"] = False

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port)
