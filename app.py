import os
import sys
from flask import Flask
from dotenv import load_dotenv
from extensions import db, login_manager, socketio
from models import User

load_dotenv()

# ✅ Fix for PyInstaller (templates & static path)
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def create_app():
    app = Flask(__name__,
                template_folder=resource_path('templates'),
                static_folder=resource_path('static'))

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///pos.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')

    db.init_app(app)
    login_manager.init_app(app)

    # ✅ FIXED SocketIO (VERY IMPORTANT)
    socketio.init_app(app, async_mode='threading')

    login_manager.login_view = 'auth.login'
    login_manager.login_message = None

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_global_data():
        from flask import session
        from flask_login import current_user
        from models import BusinessSettings

        is_spectating = 'spectate_id' in session
        spectated_user = None
        
        effective_user_id = None
        if current_user.is_authenticated:
            effective_user_id = session.get('spectate_id', current_user.id)
            if is_spectating:
                spectated_user = User.query.get(session['spectate_id'])
        
        business_settings = None
        if effective_user_id:
            business_settings = BusinessSettings.query.filter_by(user_id=effective_user_id).first()
            if not business_settings:
                business_settings = BusinessSettings(company_name="My Store", user_id=effective_user_id)
        
        if not business_settings:
            business_settings = BusinessSettings.query.first()

        return dict(
            is_spectating=is_spectating, 
            spectated_user=spectated_user,
            business_settings=business_settings
        )

    with app.app_context():
        from routes import auth_bp, pos_bp, inventory_bp, reports_bp, admin_bp, returns_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(pos_bp)
        app.register_blueprint(inventory_bp)
        app.register_blueprint(reports_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(returns_bp)

        db.create_all()
        
        # Default admin
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin', is_approved=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

    # SocketIO events
    from flask_socketio import join_room
    from flask_login import current_user

    @socketio.on('connect')
    def on_connect():
        if current_user.is_authenticated:
            join_room(f"user_{current_user.id}")
            if current_user.role == 'admin':
                join_room("admins")

    return app


if __name__ == '__main__':
    import webbrowser

    app = create_app()

    # ✅ Auto open browser (optional)
    webbrowser.open("http://127.0.0.1:5000")

    # ✅ Run app (stable for EXE)
    socketio.run(app, host='127.0.0.1', port=5000, debug=False)