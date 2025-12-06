"""Flask backend application for ERP Voice Chat System."""

import os
import traceback

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

# Load environment variables
load_dotenv(".env.local")


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Configuration
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

    # Enable CORS
    CORS(app)

    # Register blueprints
    from api.routes import duplicates_bp, erp_bp, inconsistencies_bp

    app.register_blueprint(erp_bp, url_prefix="/api/erp")
    app.register_blueprint(duplicates_bp, url_prefix="/api/duplicates")
    app.register_blueprint(inconsistencies_bp, url_prefix="/api/inconsistencies")

    # Global error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return (
            jsonify(
                {
                    "error": True,
                    "error_type": "not_found",
                    "message": "The requested resource was not found",
                    "suggested_actions": ["Check the URL and try again"],
                }
            ),
            404,
        )

    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 errors."""
        return (
            jsonify(
                {
                    "error": True,
                    "error_type": "method_not_allowed",
                    "message": "The HTTP method is not allowed for this endpoint",
                    "suggested_actions": ["Check the HTTP method and try again"],
                }
            ),
            405,
        )

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        traceback.print_exc()
        return (
            jsonify(
                {
                    "error": True,
                    "error_type": "server_error",
                    "message": "An internal server error occurred",
                    "suggested_actions": [
                        "Try again later",
                        "Contact support if the problem persists",
                    ],
                }
            ),
            500,
        )

    @app.route("/health")
    def health():
        """Health check endpoint."""
        return {"status": "healthy", "service": "erp-voice-chat-backend"}

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("FLASK_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
