from datetime import datetime, timedelta
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import func, cast, case, Date

db = SQLAlchemy()

# Ürün beğenme ilişki tablosu
product_likes = db.Table('product_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('products.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    avatar_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Beğenilen ürünler ilişkisi
    liked_products = db.relationship('Product', 
                                   secondary=product_likes,
                                   backref=db.backref('liked_by', lazy='dynamic'),
                                   lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def like_product(self, product):
        if not self.has_liked_product(product):
            self.liked_products.append(product)
            return True
        return False
    
    def unlike_product(self, product):
        if self.has_liked_product(product):
            self.liked_products.remove(product)
            return True
        return False
    
    def has_liked_product(self, product):
        return self.liked_products.filter(product_likes.c.product_id == product.id).count() > 0

    def get_default_address(self):
        """Kullanıcının varsayılan adresini döndürür."""
        return Address.query.filter_by(user_id=self.id, is_default=True).first()
    
    def get_default_credit_card(self):
        """Kullanıcının varsayılan kredi kartını döndürür."""
        return CreditCard.query.filter_by(user_id=self.id, is_default=True).first()
    
    def add_address(self, name, full_address, city, postal_code, phone, is_default=False):
        """Yeni adres ekler."""
        if is_default:
            # Diğer adreslerin varsayılan durumunu kaldır
            Address.query.filter_by(user_id=self.id, is_default=True).update({'is_default': False})
        
        address = Address(
            user_id=self.id,
            name=name,
            full_address=full_address,
            city=city,
            postal_code=postal_code,
            phone=phone,
            is_default=is_default
        )
        db.session.add(address)
        db.session.commit()
        return address
    
    def add_credit_card(self, name, card_number, card_holder, expiry_month, expiry_year, cvv, is_default=False):
        """Yeni kredi kartı ekler."""
        if is_default:
            # Diğer kartların varsayılan durumunu kaldır
            CreditCard.query.filter_by(user_id=self.id, is_default=True).update({'is_default': False})
        
        card = CreditCard(
            user_id=self.id,
            name=name,
            card_number=card_number,  # Maskelemeden kaydet
            card_holder=card_holder,
            expiry_month=expiry_month,
            expiry_year=expiry_year,
            cvv=cvv,
            is_default=is_default
        )
        db.session.add(card)
        db.session.commit()
        return card

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # Font Awesome icon class
    color = db.Column(db.String(7))  # Hex color code
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Category {self.name}>'

    @property
    def product_count(self):
        """Kategorideki aktif ürün sayısını döndürür."""
        return Product.query.filter_by(category_id=self.id, is_active=True).count()

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    discount_percent = db.Column(db.Float, default=0)  # İndirim yüzdesi
    stock = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(255))
    rating = db.Column(db.Float, default=0.0)  # 0-5 arası değer
    is_active = db.Column(db.Boolean, default=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    category = db.relationship('Category', backref=db.backref('products', lazy=True))
    
    # Beğeni sayısı
    likes_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Product {self.name}>'

    @property
    def original_price(self):
        """Ürünün orijinal fiyatını döndürür."""
        return self.price

    @property
    def current_price(self):
        """İndirimli fiyatı döndürür."""
        discount = self.discount_percent or 0  # None ise 0 kullan
        if discount > 0:
            return self.price * (1 - discount / 100)
        return self.price

    @property
    def image_path(self):
        """Ürün resminin tam yolunu döndürür."""
        if self.image_url:
            return f'uploads/{self.image_url}'
        return None

    @property
    def has_stock(self):
        """Ürünün stokta olup olmadığını kontrol eder."""
        return self.stock > 0

    @property
    def stock_status(self):
        """Ürünün stok durumunu döndürür."""
        if self.stock <= 0:
            return 'danger'
        elif self.stock < 10:
            return 'warning'
        return 'success'

    def update_likes_count(self):
        self.likes_count = self.liked_by.count()
        db.session.commit()

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255))
    is_published = db.Column(db.Boolean, default=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author = db.relationship('User', backref=db.backref('news', lazy=True))

    def __repr__(self):
        return f'<News {self.title}>'

    @property
    def image_path(self):
        """Haber resminin tam yolunu döndürür."""
        if self.image_url:
            return f'uploads/{self.image_url}'
        return None

    @property
    def excerpt(self):
        """Haberin kısa özetini döndürür."""
        if self.summary:
            return self.summary
        return self.content[:200] + '...' if len(self.content) > 200 else self.content 

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=False)
    icon = db.Column(db.String(50), nullable=False)
    icon_color = db.Column(db.String(50), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.id}>'
    
    @staticmethod
    def create_notification(message, link, icon='bell', icon_color='text-primary'):
        """Yeni bildirim oluşturur."""
        notification = Notification(
            message=message,
            link=link,
            icon=icon,
            icon_color=icon_color
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @staticmethod
    def get_unread_count():
        """Okunmamış bildirim sayısını döndürür."""
        return Notification.query.filter_by(is_read=False).count()
    
    @staticmethod
    def get_recent_notifications(limit=5):
        """Son bildirimleri döndürür."""
        return Notification.query.order_by(Notification.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def mark_as_read(notification_id=None):
        """Bildirimleri okundu olarak işaretler."""
        if notification_id:
            notification = Notification.query.get_or_404(notification_id)
            notification.is_read = True
        else:
            Notification.query.update({Notification.is_read: True})
        db.session.commit()
    
    @staticmethod
    def clear_all():
        """Tüm bildirimleri siler."""
        Notification.query.delete()
        db.session.commit()

class Address(db.Model):
    __tablename__ = 'addresses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Adres adı (örn: "Ev", "İş")
    full_address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(50), nullable=False)
    postal_code = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('addresses', lazy=True))
    
    def __repr__(self):
        return f'<Address {self.name} - {self.user.username}>'

class CreditCard(db.Model):
    __tablename__ = 'credit_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Kart adı (örn: "Ana Kart")
    card_number = db.Column(db.String(19), nullable=False)  # Maskelenmiş kart numarası
    card_holder = db.Column(db.String(100), nullable=False)
    expiry_month = db.Column(db.Integer, nullable=False)
    expiry_year = db.Column(db.Integer, nullable=False)
    cvv = db.Column(db.String(4), nullable=False)  # CVV alanı eklendi
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('credit_cards', lazy=True))
    
    def __repr__(self):
        return f'<CreditCard {self.name} - {self.user.username}>'

    def __init__(self, user_id, name, card_number, card_holder, expiry_month, expiry_year, cvv, is_default=False):
        self.user_id = user_id
        self.name = name
        self.card_number = card_number
        self.card_holder = card_holder
        self.expiry_month = expiry_month
        self.expiry_year = expiry_year
        self.cvv = cvv
        self.is_default = is_default

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'card_number': f"**** **** **** {self.card_number[-4:]}",
            'card_holder': self.card_holder,
            'expiry_month': self.expiry_month,
            'expiry_year': self.expiry_year,
            'cvv': '***',  # CVV maskeleme
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'), nullable=False)
    credit_card_id = db.Column(db.Integer, db.ForeignKey('credit_cards.id'), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processing, shipped, delivered, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('orders', lazy=True))
    address = db.relationship('Address', backref=db.backref('orders', lazy=True))
    credit_card = db.relationship('CreditCard', backref=db.backref('orders', lazy=True))
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.id} - {self.user.username}>'
    
    @property
    def status_display(self):
        """Sipariş durumunu görüntülemek için kullanılır."""
        status_map = {
            'pending': 'Beklemede',
            'processing': 'İşleniyor',
            'shipped': 'Kargoya Verildi',
            'delivered': 'Teslim Edildi',
            'cancelled': 'İptal Edildi'
        }
        return status_map.get(self.status, self.status)
    
    @property
    def status_color(self):
        """Sipariş durumuna göre renk döndürür."""
        status_colors = {
            'pending': 'warning',
            'processing': 'info',
            'shipped': 'primary',
            'delivered': 'success',
            'cancelled': 'danger'
        }
        return status_colors.get(self.status, 'secondary')
    
    @property
    def item_count(self):
        """Siparişteki toplam ürün sayısını döndürür."""
        return sum(item.quantity for item in self.items)

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # Sipariş anındaki ürün fiyatı
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    product = db.relationship('Product', backref=db.backref('order_items', lazy=True))
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'
    
    @property
    def total_price(self):
        """Ürünün toplam fiyatını döndürür."""
        return self.price * self.quantity

class Visitor(db.Model):
    __tablename__ = 'visitors'
    
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=False)
    user_agent = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_authenticated = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('visits', lazy=True))

    def __repr__(self):
        return f'<Visitor {self.ip} - {self.created_at}>'

    @staticmethod
    def get_daily_stats(days=7):
        try:
            from sqlalchemy import case, func, cast, Integer
            
            return db.session.query(
                func.strftime('%d.%m', func.date(Visitor.created_at)).label('date'),
                func.count(Visitor.id).label('total_visits'),
                func.sum(cast(Visitor.is_authenticated, Integer)).label('authenticated_visits'),
                func.sum(cast(Visitor.is_admin, Integer)).label('admin_visits'),
                func.sum(cast(~Visitor.is_authenticated, Integer)).label('guest_visits')
            ).filter(
                Visitor.created_at >= datetime.utcnow() - timedelta(days=days)
            ).group_by(
                func.date(Visitor.created_at)
            ).order_by(
                func.date(Visitor.created_at)
            ).all()
        except Exception as e:
            current_app.logger.error(f"Ziyaretçi istatistikleri hesaplanırken hata: {str(e)}")
            return []

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 arası değer
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # İlişkiler
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))
    product = db.relationship('Product', backref=db.backref('reviews', lazy=True))

    def __repr__(self):
        return f'<Review {self.id} - {self.rating} stars>'

    @staticmethod
    def get_product_reviews(product_id, limit=None):
        """Ürüne ait değerlendirmeleri döndürür."""
        query = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc())
        if limit:
            return query.limit(limit).all()
        return query.all()

    @staticmethod
    def get_user_review(user_id, product_id):
        """Kullanıcının ürüne ait değerlendirmesini döndürür."""
        return Review.query.filter_by(user_id=user_id, product_id=product_id).first()

    @staticmethod
    def update_product_rating(product_id):
        """Ürünün ortalama puanını günceller."""
        product = Product.query.get(product_id)
        if product:
            avg_rating = db.session.query(db.func.avg(Review.rating)).filter_by(product_id=product_id).scalar()
            product.rating = round(float(avg_rating or 0), 1)
            db.session.commit() 