from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    @app.after_request
    def add_header(response):
        # Force browser to never cache static files/pages during dev
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    # register routes
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app
