from app import create_app

app = create_app()

if __name__ == "__main__":
    print("Open http://localhost:8080 in your browser")
    app.run(port=8080)
