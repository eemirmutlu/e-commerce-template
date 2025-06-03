from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, make_response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import Address, CreditCard, Product, Category, News, User, Notification, Visitor, Order
from app.forms import ProductForm, CategoryForm, NewsForm
import os
from datetime import datetime, timedelta
import logging
from sqlalchemy import func, desc, cast, Integer
from app.utils import admin_required
import requests
from functools import wraps
import json
import csv
from io import StringIO

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)

@admin_bp.before_request
@login_required
@admin_required
def before_request():
    pass

@admin_bp.before_request
def track_admin_visit():
    if current_user.is_authenticated and current_user.is_admin:
        visitor = Visitor(
            ip=request.remote_addr,
            user_agent=request.user_agent.string,
            is_authenticated=True,
            is_admin=True,
            user_id=current_user.id
        )
        db.session.add(visitor)
        db.session.commit()

def allowed_file(filename):
    """Dosya uzantısının izin verilen türlerden olup olmadığını kontrol eder."""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_product_image(file):
    """Ürün resmini kaydeder ve dosya adını döndürür."""
    try:
        if file and file.filename and allowed_file(file.filename):
            # Güvenli dosya adı oluştur
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{secure_filename(file.filename)}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            
            # Dosyayı kaydet
            file.save(file_path)
            return filename
        return None
    except Exception as e:
        logger.error(f"Resim kaydedilirken hata oluştu: {str(e)}")
        raise

def delete_product_image(filename):
    """Ürün resmini siler."""
    if filename:
        try:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Resim silinirken hata oluştu: {str(e)}")

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Kullanıcı ve ziyaretçi verileri
    users = User.query.order_by(User.created_at.desc()).all()
    visitors = Visitor.query.order_by(Visitor.created_at.desc()).limit(10).all()
    
    # Son 7 günlük ziyaretçi istatistikleri
    visitor_stats = db.session.query(
        func.strftime('%d.%m', Visitor.created_at).label('date'),
        func.count(Visitor.id).label('total_visits'),
        func.sum(cast(Visitor.is_authenticated, Integer)).label('authenticated_visits'),
        func.sum(cast(Visitor.is_admin, Integer)).label('admin_visits'),
        func.sum(cast(Visitor.is_authenticated == 0, Integer)).label('guest_visits')
    ).filter(
        Visitor.created_at >= datetime.utcnow() - timedelta(days=7)
    ).group_by(
        func.strftime('%d.%m', Visitor.created_at)
    ).order_by(
        func.strftime('%d.%m', Visitor.created_at)
    ).all()
    
    # Genel istatistikler
    stats = {
        'total_products': Product.query.count(),
        'active_products': Product.query.filter_by(is_active=True).count(),
        'total_categories': Category.query.count(),
        'active_categories': Category.query.filter_by(is_active=True).count(),
        'total_news': News.query.count(),
        'published_news': News.query.filter_by(is_published=True).count(),
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'low_stock_products': Product.query.filter(Product.stock < 10, Product.stock > 0).count(),
        'out_of_stock_products': Product.query.filter_by(stock=0).count(),
        'total_stock_value': db.session.query(func.sum(Product.price * Product.stock)).scalar() or 0,
        'total_visits': Visitor.query.count(),
        'authenticated_visits': Visitor.query.filter_by(is_authenticated=True).count(),
        'guest_visits': Visitor.query.filter_by(is_authenticated=False).count(),
        'total_orders': Order.query.count(),
        'pending_orders': Order.query.filter_by(status='pending').count(),
        'completed_orders': Order.query.filter(Order.status.in_(['delivered', 'shipped'])).count()
    }
    
    # Son eklenen ürünler
    recent_products = Product.query.join(Category).order_by(Product.created_at.desc()).limit(5).all()
    
    # Son haberler
    recent_news = News.query.join(User).order_by(News.created_at.desc()).limit(5).all()
    
    # Son siparişler
    recent_orders = Order.query.join(User).order_by(Order.created_at.desc()).limit(5).all()
    
    # Kategori istatistikleri
    category_stats = db.session.query(
        Category.name,
        func.count(Product.id).label('product_count'),
        func.sum(Product.stock).label('total_stock'),
        func.coalesce(func.avg(Product.price), 0).label('avg_price')
    ).outerjoin(Product).group_by(Category.id).order_by(func.count(Product.id).desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         users=users,
                         visitors=visitors,
                         visitor_stats=visitor_stats,
                         stats=stats,
                         recent_products=recent_products,
                         recent_news=recent_news,
                         recent_orders=recent_orders,
                         category_stats=category_stats)

@admin_bp.route('/products')
def manage_products():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get filter parameters
    category_id = request.args.get('category', type=int)
    status = request.args.get('status')
    search = request.args.get('search', '')
    
    # Build query
    query = Product.query
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    if search:
        query = query.filter(
            (Product.name.ilike(f'%{search}%')) |
            (Product.description.ilike(f'%{search}%'))
        )
    
    # Get categories for filter
    categories = Category.query.filter_by(is_active=True).all()
    
    # Get paginated products
    pagination = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    products = pagination.items
    
    return render_template('admin/manage_products.html',
                         products=products,
                         categories=categories,
                         pagination=pagination)

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    try:
        form = ProductForm()
        # Kategori seçeneklerini doldur
        form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
        
        if form.validate_on_submit():
            try:
                # Resim yükleme işlemi
                image_filename = None
                if 'image' in request.files:
                    image_filename = save_product_image(request.files['image'])
                
                # Yeni ürün oluştur
                product = Product(
                    name=form.name.data,
                    description=form.description.data,
                    price=form.price.data,
                    stock=form.stock.data,
                    category_id=form.category_id.data,
                    image_url=image_filename
                )
                
                db.session.add(product)
                db.session.commit()
                
                # Yeni ürün bildirimi oluştur
                create_new_product_notification(product)
                
                flash('Ürün başarıyla eklendi!', 'success')
                return redirect(url_for('admin.manage_products'))
                
            except Exception as e:
                db.session.rollback()
                # Yüklenen resmi sil
                if image_filename:
                    delete_product_image(image_filename)
                logger.error(f"Ürün eklenirken hata oluştu: {str(e)}")
                flash('Ürün eklenirken bir hata oluştu.', 'danger')
        
        return render_template('admin/product_form.html', form=form, product=None)
        
    except Exception as e:
        logger.error(f"Ürün ekleme sayfası yüklenirken hata oluştu: {str(e)}")
        flash('Bir hata oluştu.', 'danger')
        return redirect(url_for('admin.manage_products'))

@admin_bp.route('/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(id):
    try:
        product = Product.query.get_or_404(id)
        form = ProductForm(obj=product)
        form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
        
        if form.validate_on_submit():
            try:
                # Resim yükleme işlemi
                if 'image' in request.files and request.files['image'].filename:
                    # Eski resmi sil
                    if product.image_url:
                        delete_product_image(product.image_url)
                    
                    # Yeni resmi kaydet
                    image_filename = save_product_image(request.files['image'])
                    if image_filename:
                        product.image_url = image_filename
                
                # Ürün bilgilerini güncelle
                product.name = form.name.data
                product.description = form.description.data
                product.price = form.price.data
                product.stock = form.stock.data
                product.category_id = form.category_id.data
                
                db.session.commit()
                flash('Ürün başarıyla güncellendi!', 'success')
                return redirect(url_for('admin.manage_products'))
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Ürün güncellenirken hata oluştu: {str(e)}")
                flash('Ürün güncellenirken bir hata oluştu.', 'danger')
        
        return render_template('admin/product_form.html', form=form, product=product)
        
    except Exception as e:
        logger.error(f"Ürün düzenleme sayfası yüklenirken hata oluştu: {str(e)}")
        flash('Bir hata oluştu.', 'danger')
        return redirect(url_for('admin.manage_products'))

@admin_bp.route('/products/<int:product_id>/delete', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    try:
        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting product: {str(e)}')
        return jsonify({'success': False, 'message': 'Ürün silinirken bir hata oluştu.'})

@admin_bp.route('/categories')
def manage_categories():
    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/manage_categories.html', categories=categories)

@admin_bp.route('/categories/add', methods=['POST'])
def add_category():
    name = request.form.get('name')
    description = request.form.get('description')
    icon = request.form.get('icon')
    color = request.form.get('color')
    is_active = request.form.get('is_active') == 'on'
    
    category = Category(
        name=name,
        description=description,
        icon=icon,
        color=color,
        is_active=is_active
    )
    
    try:
        db.session.add(category)
        db.session.commit()
        flash('Kategori başarıyla eklendi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Kategori eklenirken bir hata oluştu.', 'error')
        current_app.logger.error(f'Error adding category: {str(e)}')
    
    return redirect(url_for('admin.manage_categories'))

@admin_bp.route('/categories/<int:category_id>/edit', methods=['POST'])
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    
    category.name = request.form.get('name')
    category.description = request.form.get('description')
    category.icon = request.form.get('icon')
    category.color = request.form.get('color')
    category.is_active = request.form.get('is_active') == 'on'
    
    try:
        db.session.commit()
        flash('Kategori başarıyla güncellendi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Kategori güncellenirken bir hata oluştu.', 'error')
        current_app.logger.error(f'Error updating category: {str(e)}')
    
    return redirect(url_for('admin.manage_categories'))

@admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    
    try:
        db.session.delete(category)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting category: {str(e)}')
        return jsonify({'success': False, 'message': 'Kategori silinirken bir hata oluştu.'})

@admin_bp.route('/news')
def manage_news():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get filter parameters
    status = request.args.get('status')
    search = request.args.get('search', '')
    
    # Build query
    query = News.query
    
    if status == 'published':
        query = query.filter_by(is_published=True)
    elif status == 'draft':
        query = query.filter_by(is_published=False)
    if search:
        query = query.filter(
            (News.title.ilike(f'%{search}%')) |
            (News.content.ilike(f'%{search}%'))
        )
    
    # Get paginated news
    pagination = query.order_by(News.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    news_list = pagination.items
    
    return render_template('admin/manage_news.html',
                         news_list=news_list,
                         pagination=pagination)

@admin_bp.route('/news/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_news():
    form = NewsForm()
    
    if form.validate_on_submit():
        try:
            news = News(
                title=form.title.data,
                summary=form.summary.data,
                content=form.content.data,
                is_published=form.is_published.data,
                author_id=current_user.id
            )
            
            if form.image.data and form.image.data.filename:
                try:
                    # Dosya uzantısı kontrolü
                    if not allowed_file(form.image.data.filename):
                        raise ValueError('Geçersiz dosya formatı. Sadece PNG, JPG, JPEG ve GIF dosyaları yüklenebilir.')
                    
                    # Güvenli dosya adı oluştur
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{secure_filename(form.image.data.filename)}"
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    
                    # Dosyayı kaydet
                    form.image.data.save(file_path)
                    logger.info(f"News image saved successfully: {filename}")
                    news.image_url = filename
                except Exception as e:
                    logger.error(f"Error saving news image: {str(e)}")
                    flash(f'Resim yüklenirken hata oluştu: {str(e)}', 'danger')
                    return render_template('admin/news_form.html', form=form)
            
            db.session.add(news)
            db.session.commit()
            
            # Yeni haber bildirimi oluştur
            create_news_notification(news)
            
            logger.info(f"News article added successfully: {news.title}")
            flash('Haber başarıyla eklendi!', 'success')
            return redirect(url_for('admin.manage_news'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding news article: {str(e)}")
            flash(f'Haber eklenirken bir hata oluştu: {str(e)}', 'danger')
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return render_template('admin/news_form.html', form=form)

@admin_bp.route('/news/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_news(id):
    news = News.query.get_or_404(id)
    form = NewsForm(obj=news)
    
    if form.validate_on_submit():
        try:
            news.title = form.title.data
            news.summary = form.summary.data
            news.content = form.content.data
            news.is_published = form.is_published.data
            
            if form.image.data and form.image.data.filename:
                # Delete old image if exists
                if news.image_url:
                    old_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], news.image_url)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                
                try:
                    # Güvenli dosya adı oluştur
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{secure_filename(form.image.data.filename)}"
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    
                    # Dosyayı kaydet
                    form.image.data.save(file_path)
                    logger.info(f"News image updated successfully: {filename}")
                    news.image_url = filename
                except Exception as e:
                    logger.error(f"Error updating news image: {str(e)}")
                    flash(f'Resim güncellenirken hata oluştu: {str(e)}', 'danger')
                    return render_template('admin/news_form.html', form=form, news=news)
            
            db.session.commit()
            flash('Haber başarıyla güncellendi!', 'success')
            return redirect(url_for('admin.manage_news'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating news article: {str(e)}")
            flash(f'Haber güncellenirken bir hata oluştu: {str(e)}', 'danger')
    
    return render_template('admin/news_form.html', form=form, news=news)

@admin_bp.route('/news/<int:news_id>/delete', methods=['POST'])
def delete_news(news_id):
    news = News.query.get_or_404(news_id)
    
    try:
        db.session.delete(news)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting news: {str(e)}')
        return jsonify({'success': False, 'message': 'Haber silinirken bir hata oluştu.'})

@admin_bp.context_processor
def inject_notifications():
    """Her template'e bildirimleri ekler."""
    notifications = Notification.get_recent_notifications()
    return dict(notifications=notifications)

@admin_bp.route('/notifications')
@admin_required
def notifications():
    """Tüm bildirimleri listeler."""
    page = request.args.get('page', 1, type=int)
    notifications = Notification.query.order_by(
        Notification.created_at.desc()
    ).paginate(page=page, per_page=20)
    
    return render_template('admin/notifications.html', notifications=notifications)

@admin_bp.route('/notifications/mark-read/<int:notification_id>')
@admin_required
def mark_notification_read(notification_id):
    """Bildirimi okundu olarak işaretler."""
    notification = Notification.query.get_or_404(notification_id)
    notification.is_read = True
    db.session.commit()
    return redirect(notification.link)

@admin_bp.route('/notifications/mark-all-read')
@admin_required
def mark_all_read():
    """Tüm bildirimleri okundu olarak işaretler."""
    Notification.mark_as_read()
    flash('Tüm bildirimler okundu olarak işaretlendi.', 'success')
    return redirect(url_for('admin.notifications'))

@admin_bp.route('/notifications/clear')
@admin_required
def clear_notifications():
    """Tüm bildirimleri temizler."""
    Notification.clear_all()
    flash('Tüm bildirimler temizlendi.', 'success')
    return redirect(url_for('admin.notifications'))

# Kullanıcı kaydı olduğunda bildirim oluştur
def create_user_notification(user):
    """Yeni kullanıcı kaydı için bildirim oluşturur."""
    Notification.create_notification(
        message=f'Yeni kullanıcı kaydı: {user.username}',
        link=url_for('admin.manage_users'),
        icon='user-plus',
        icon_color='text-success'
    )

# Sipariş oluştuğunda bildirim oluştur
def create_order_notification(order):
    """Yeni sipariş için bildirim oluşturur."""
    Notification.create_notification(
        message=f'Yeni sipariş alındı: #{order.id}',
        link=url_for('admin.manage_orders'),
        icon='shopping-cart',
        icon_color='text-primary'
    )

# Ürün stok azaldığında bildirim oluştur
def create_low_stock_notification(product):
    """Düşük stok için bildirim oluşturur."""
    Notification.create_notification(
        message=f'Düşük stok uyarısı: {product.name}',
        link=url_for('admin.edit_product', id=product.id),
        icon='exclamation-triangle',
        icon_color='text-warning'
    )

# Yeni ürün eklendiğinde bildirim oluştur
def create_new_product_notification(product):
    """Yeni ürün için bildirim oluşturur."""
    Notification.create_notification(
        message=f'Yeni ürün eklendi: {product.name}',
        link=url_for('admin.edit_product', id=product.id),
        icon='box',
        icon_color='text-info'
    )

# Yeni haber eklendiğinde bildirim oluştur
def create_news_notification(news):
    """Yeni haber için bildirim oluşturur."""
    Notification.create_notification(
        message=f'Yeni haber eklendi: {news.title}',
        link=url_for('admin.edit_news', id=news.id),
        icon='newspaper',
        icon_color='text-primary'
    )

# Stok güncelleme fonksiyonunu güncelle
def update_product_stock(product, new_stock):
    """Ürün stoğunu günceller ve gerekirse bildirim oluşturur."""
    old_stock = product.stock
    product.stock = new_stock
    
    # Stok kritik seviyenin altına düştüyse bildirim oluştur
    if new_stock <= 5 and old_stock > 5:
        create_low_stock_notification(product)
    
    db.session.commit()

@admin_bp.route('/visitor-details')
@login_required
@admin_required
def visitor_details():
    days = request.args.get('days', default=7, type=int)
    page = request.args.get('page', default=1, type=int)
    
    # İstatistikleri al
    visitor_stats = db.session.query(
        func.strftime('%d.%m', Visitor.created_at).label('date'),
        func.count(Visitor.id).label('total_visits'),
        func.sum(cast(Visitor.is_authenticated, Integer)).label('authenticated_visits'),
        func.sum(cast(Visitor.is_admin, Integer)).label('admin_visits'),
        func.sum(cast(Visitor.is_authenticated == 0, Integer)).label('guest_visits')
    ).filter(
        Visitor.created_at >= datetime.utcnow() - timedelta(days=days)
    ).group_by(
        func.strftime('%d.%m', Visitor.created_at)
    ).order_by(
        func.strftime('%d.%m', Visitor.created_at)
    ).all()
    
    # Tüm ziyaretçileri al
    visitors = Visitor.query.filter(
        Visitor.created_at >= datetime.utcnow() - timedelta(days=days)
    ).order_by(Visitor.created_at.desc()).all()
    
    # İstatistikleri hesapla
    total_visits = sum(stat.total_visits for stat in visitor_stats) or 1  # Sıfıra bölmeyi önlemek için
    authenticated_visits = sum(stat.authenticated_visits for stat in visitor_stats) or 0
    admin_visits = sum(stat.admin_visits for stat in visitor_stats) or 0
    guest_visits = sum(stat.guest_visits for stat in visitor_stats) or 0
    
    stats = {
        'total_visits': total_visits,
        'authenticated_visits': authenticated_visits,
        'admin_visits': admin_visits,
        'guest_visits': guest_visits
    }
    
    return render_template('admin/visitor_details.html',
                         visitor_stats=visitor_stats,
                         visitors=visitors,
                         stats=stats,
                         days=days)

@admin_bp.route('/visitor-ip-details/<ip>')
@login_required
@admin_required
def visitor_ip_details(ip):
    try:
        # IP-API'den IP detaylarını al
        response = requests.get(
            f'http://ip-api.com/json/{ip}',
            timeout=10,  # Timeout süresini artır
            headers={'User-Agent': 'Mozilla/5.0'}  # User-Agent ekle
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return jsonify({
                    'ip': ip,
                    'country': data.get('country'),
                    'city': data.get('city'),
                    'isp': data.get('isp'),
                    'org': data.get('org'),
                    'region': data.get('regionName'),
                    'timezone': data.get('timezone')
                })
            else:
                current_app.logger.warning(f"IP-API başarısız yanıt: {data.get('message')} - IP: {ip}")
                return jsonify({
                    'ip': ip,
                    'error': data.get('message', 'IP detayları alınamadı')
                }), 404
    except requests.Timeout:
        current_app.logger.error(f"IP-API timeout: {ip}")
        return jsonify({
            'ip': ip,
            'error': 'IP detayları zaman aşımına uğradı'
        }), 504
    except requests.RequestException as e:
        current_app.logger.error(f"IP-API isteği başarısız: {str(e)} - IP: {ip}")
        return jsonify({
            'ip': ip,
            'error': 'IP detayları alınırken bir hata oluştu'
        }), 500
    except Exception as e:
        current_app.logger.error(f"Beklenmeyen hata: {str(e)} - IP: {ip}")
        return jsonify({
            'ip': ip,
            'error': 'Beklenmeyen bir hata oluştu'
        }), 500

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def user_details(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('admin/user_details.html', user=user)

@admin_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    try:
        user.username = request.form['username']
        user.email = request.form['email']
        user.is_active = 'is_active' in request.form
        
        db.session.commit()
        flash('Kullanıcı başarıyla güncellendi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Kullanıcı güncellenirken bir hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    try:
        # Kullanıcının siparişlerini kontrol et
        if user.orders:
            flash('Siparişi olan kullanıcılar silinemez', 'error')
            return redirect(url_for('admin.users'))
        
        db.session.delete(user)
        db.session.commit()
        flash('Kullanıcı başarıyla silindi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Kullanıcı silinirken bir hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/export', methods=['POST'])
@login_required
@admin_required
def export_users():
    format = request.form.get('format', 'csv')
    include_orders = 'include_orders' in request.form
    include_addresses = 'include_addresses' in request.form
    include_cards = 'include_cards' in request.form
    
    users = User.query.all()
    data = []
    
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
            'is_active': user.is_active
        }
        
        if include_orders:
            user_data['orders'] = [{
                'id': order.id,
                'status': order.status,
                'total_amount': float(order.total_amount),
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for order in user.orders]
        
        if include_addresses:
            user_data['addresses'] = [{
                'id': addr.id,
                'name': addr.name,
                'full_address': addr.full_address,
                'city': addr.city,
                'postal_code': addr.postal_code,
                'phone': addr.phone,
                'is_default': addr.is_default
            } for addr in user.addresses]
        
        if include_cards:
            user_data['credit_cards'] = [{
                'id': card.id,
                'name': card.name,
                'card_number': card.card_number,
                'card_holder': card.card_holder,
                'expiry_month': card.expiry_month,
                'expiry_year': card.expiry_year,
                'is_default': card.is_default
            } for card in user.credit_cards]
        
        data.append(user_data)
    
    if format == 'json':
        response = make_response(json.dumps(data, indent=2))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = 'attachment; filename=users.json'
    else:  # CSV
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=users.csv'
    
    return response

@admin_bp.route('/users/import', methods=['POST'])
@login_required
@admin_required
def import_users():
    if 'file' not in request.files:
        flash('Dosya seçilmedi', 'error')
        return redirect(url_for('admin.users'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Dosya seçilmedi', 'error')
        return redirect(url_for('admin.users'))
    
    try:
        if file.filename.endswith('.json'):
            data = json.load(file)
        elif file.filename.endswith(('.csv', '.xlsx', '.xls')):
            # CSV/Excel okuma işlemi burada yapılacak
            pass
        else:
            flash('Desteklenmeyen dosya formatı', 'error')
            return redirect(url_for('admin.users'))
        
        for user_data in data:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                is_active=user_data.get('is_active', True)
            )
            user.set_password('changeme')  # Varsayılan şifre
            db.session.add(user)
            
            # Adresleri ekle
            for addr_data in user_data.get('addresses', []):
                address = Address(
                    user=user,
                    name=addr_data['name'],
                    full_address=addr_data['full_address'],
                    city=addr_data['city'],
                    postal_code=addr_data['postal_code'],
                    phone=addr_data['phone'],
                    is_default=addr_data.get('is_default', False)
                )
                db.session.add(address)
            
            # Kredi kartlarını ekle
            for card_data in user_data.get('credit_cards', []):
                card = CreditCard(
                    user=user,
                    name=card_data['name'],
                    card_number=card_data['card_number'],
                    card_holder=card_data['card_holder'],
                    expiry_month=card_data['expiry_month'],
                    expiry_year=card_data['expiry_year'],
                    is_default=card_data.get('is_default', False)
                )
                db.session.add(card)
        
        db.session.commit()
        flash('Kullanıcılar başarıyla içe aktarıldı', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Kullanıcılar içe aktarılırken bir hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    # Get filter parameters
    status = request.args.get('status')
    search = request.args.get('search', '')
    
    # Build query
    query = Order.query.join(User)
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(
            (Order.id.ilike(f'%{search}%')) |
            (User.username.ilike(f'%{search}%'))
        )
    
    # Get orders ordered by creation date
    orders = query.order_by(Order.created_at.desc()).all()
    
    return render_template('admin/orders.html', orders=orders)

@admin_bp.route('/order/<int:order_id>')
@login_required
@admin_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_detail.html', order=order)

@admin_bp.route('/order/update-status', methods=['POST'])
@login_required
@admin_required
def update_order_status():
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        new_status = data.get('status')
        
        if not order_id or not new_status:
            return jsonify({'success': False, 'message': 'Geçersiz sipariş ID veya durum'}), 400
        
        order = Order.query.get_or_404(order_id)
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Sipariş durumu değişikliği bildirimi oluştur
        create_order_notification(order)
        
        return jsonify({
            'success': True,
            'message': 'Sipariş durumu başarıyla güncellendi'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Sipariş durumu güncellenirken hata: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 400 