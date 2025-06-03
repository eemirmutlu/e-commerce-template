import os
from flask import Flask, request
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import logging
from config import Config
from app.models import db, User  # Import User model along with db
from datetime import datetime, timedelta

# Initialize extensions
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

def create_admin_user():
    from app.models import User
    admin = User.query.filter((User.username == 'admin') | (User.email == 'admin@techstore.com')).first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@techstore.com',
            is_admin=True,
            is_active=True,
            avatar_url=None
        )
        admin.set_password('admin123')
        db.session.add(admin)
        try:
            db.session.commit()
            print('Admin kullanıcısı otomatik olarak oluşturuldu!')
        except Exception as e:
            db.session.rollback()
            print(f'Admin oluşturulurken hata: {str(e)}')

def timeago(dt, default="az önce"):
    """İnsan okunabilir zaman farkı döndürür."""
    now = datetime.utcnow()
    diff = now - dt if dt else None
    if not diff:
        return default
    seconds = diff.total_seconds()
    periods = [
        (seconds // 31536000, "yıl"),
        (seconds // 2592000, "ay"),
        (seconds // 604800, "hafta"),
        (seconds // 86400, "gün"),
        (seconds // 3600, "saat"),
        (seconds // 60, "dakika"),
        (seconds, "saniye"),
    ]
    for period, singular in periods:
        if period >= 1:
            return f"{int(period)} {singular} önce"
    return default

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Debug modunu aktifleştir
    app.debug = True
    
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Ensure upload folder exists with proper permissions
    upload_folder = app.config['UPLOAD_FOLDER']
    try:
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, mode=0o755, exist_ok=True)
            logger.info(f"Created upload folder at: {upload_folder}")
        else:
            # Ensure proper permissions on existing folder
            os.chmod(upload_folder, 0o755)
            logger.info(f"Verified upload folder permissions at: {upload_folder}")
    except Exception as e:
        logger.error(f"Error setting up upload folder: {str(e)}")
        raise
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Configure login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Bu sayfayı görüntülemek için giriş yapmalısınız.'
    login_manager.login_message_category = 'warning'
    
    # Register blueprints
    from app.routes import main_bp
    from app.auth_routes import auth_bp
    from app.admin_routes import admin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    
    # Register template filters
    @app.template_filter('currency')
    def currency_filter(value):
        """Para birimini formatlar."""
        try:
            return f"₺{value:,.2f}"
        except (ValueError, TypeError):
            return "₺0.00"
    
    @app.template_filter('timeago')
    def timeago_filter(dt):
        return timeago(dt)
    
    @app.template_filter('datetime')
    def datetime_filter(dt, format='%d.%m.%Y %H:%M'):
        """Format datetime objects in templates."""
        if dt is None:
            return ''
        return dt.strftime(format)
    
    # Create database tables and admin user
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        # Create admin user if it doesn't exist
        if not User.query.filter_by(username='admin').first():
            create_admin_user()
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    @app.before_request
    def track_visitor():
        """Her istek öncesi ziyaretçiyi kaydet."""
        from app.models import Visitor
        from flask_login import current_user
        
        # Admin paneli ve statik dosyalar için takip yapma
        if not request.path.startswith('/admin') and not request.path.startswith('/static'):
            try:
                # Aynı IP'den son 1 dakika içinde kayıt var mı kontrol et
                last_visit = Visitor.query.filter(
                    Visitor.ip == request.remote_addr,
                    Visitor.created_at >= datetime.utcnow() - timedelta(minutes=1)
                ).first()
                
                if not last_visit:
                    visitor = Visitor(
                        ip=request.remote_addr,
                        user_agent=request.user_agent.string,
                        is_authenticated=current_user.is_authenticated,
                        is_admin=current_user.is_authenticated and current_user.is_admin,
                        user_id=current_user.id if current_user.is_authenticated else None
                    )
                    db.session.add(visitor)
                    db.session.commit()
                    app.logger.info(f"Yeni ziyaretçi kaydedildi: {visitor.ip}")
            except Exception as e:
                app.logger.error(f"Ziyaretçi kaydedilirken hata: {str(e)}", exc_info=True)
                db.session.rollback()
    
    return app 