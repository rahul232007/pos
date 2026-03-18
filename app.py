import os
from flask import Flask
from dotenv import load_dotenv
from extensions import db, login_manager, socketio
from models import User

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///pos.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)

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
                # Provide default settings if none found for user
                business_settings = BusinessSettings(company_name="My Store", user_id=effective_user_id)
        
        if not business_settings:
            business_settings = BusinessSettings.query.first() # Fallback

        return dict(
            is_spectating=is_spectating, 
            spectated_user=spectated_user,
            business_settings=business_settings
        )

    with app.app_context():
        # Register blueprints (to be created)
        from routes import auth_bp, pos_bp, inventory_bp, reports_bp, admin_bp, returns_bp
        app.register_blueprint(auth_bp)
        app.register_blueprint(pos_bp)
        app.register_blueprint(inventory_bp)
        app.register_blueprint(reports_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(returns_bp)

        db.create_all()
        
        # Create default admin if not exists
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
            # Join personal room
            join_room(f"user_{current_user.id}")
            # Join admin room if applicable
            if current_user.role == 'admin':
                join_room("admins")

    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
