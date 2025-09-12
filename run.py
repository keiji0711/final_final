# 1️⃣ Monkey-patch **before everything else**
import eventlet
eventlet.monkey_patch()

# 2️⃣ Now import the rest
from flask import Flask
from flask_socketio import SocketIO
from app.routes.dashboard import bp as dashboard_bp
from app.routes.events import bp as events_bp, set_socketio
from app.routes.auth import bp as auth_bp
from app.routes.stud_profiling import bp as stud_profiling_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = "supersecret"

# Initialize SocketIO with Eventlet
socketio = SocketIO(app, cors_allowed_origins="*")

# Inject socketio into events blueprint
set_socketio(socketio)

# Register blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(events_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(stud_profiling_bp)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5050, debug=True)
