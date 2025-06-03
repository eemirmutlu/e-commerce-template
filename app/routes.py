from flask import Blueprint, render_template, request, abort, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Product, Category, News, User, Order, OrderItem, Notification, Review, Address, CreditCard
from sqlalchemy import or_
from app.forms import LoginForm, RegisterForm, ContactForm
from app import db
from app.admin_routes import create_user_notification, create_order_notification
from datetime import datetime
from decimal import Decimal
import json
import csv
from io import StringIO
from flask import make_response
from functools import wraps

main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def get_cart():
    """Sepeti session'dan alır veya yeni bir sepet oluşturur."""
    return session.get('cart', {})

def save_cart(cart):
    """Sepeti session'a kaydeder."""
    session['cart'] = cart

@main_bp.route('/')
def index():
    # Get latest products
    products = Product.query.order_by(Product.created_at.desc()).limit(8).all()
    # Get all categories
    categories = Category.query.all()
    
    return render_template('index.html', 
                         products=products,
                         categories=categories)

@main_bp.route('/products')
def products():
    category_id = request.args.get('category_id', type=int)
    search_query = request.args.get('search', '')
    sort = request.args.get('sort', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    in_stock = request.args.get('in_stock') == 'true'
    page = request.args.get('page', 1, type=int)
    
    query = Product.query
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search_query:
        query = query.filter(or_(
            Product.name.ilike(f'%{search_query}%'),
            Product.description.ilike(f'%{search_query}%')
        ))
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    if in_stock:
        query = query.filter(Product.stock > 0)
    
    # Sıralama
    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort == 'name_asc':
        query = query.order_by(Product.name.asc())
    elif sort == 'name_desc':
        query = query.order_by(Product.name.desc())
    elif sort == 'newest':
        query = query.order_by(Product.created_at.desc())
    else:
        query = query.order_by(Product.created_at.desc())
    
    # Sayfalama
    pagination = query.paginate(page=page, per_page=12, error_out=False)
    products = pagination.items
    
    categories = Category.query.all()
    
    return render_template('main/products.html',
                         products=products,
                         categories=categories,
                         pagination=pagination,
                         category_id=category_id,
                         search_query=search_query,
                         sort=sort,
                         min_price=min_price,
                         max_price=max_price,
                         in_stock=in_stock)

@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id
    ).limit(4).all()
    
    return render_template('product_detail.html',
                         product=product,
                         related_products=related_products)

@main_bp.route('/news')
def news():
    news_list = News.query.order_by(News.created_at.desc()).all()
    return render_template('news.html', news=news_list)

@main_bp.route('/news/<int:news_id>')
def news_detail(news_id):
    news_item = News.query.get_or_404(news_id)
    recent_news = News.query.filter(News.id != news_id).order_by(News.created_at.desc()).limit(5).all()
    categories = Category.query.all()
    return render_template('news_detail.html', 
                         news=news_item,
                         recent_news=recent_news,
                         categories=categories)

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Form verilerini al
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # TODO: E-posta gönderme işlemi burada yapılacak
        
        flash('Mesajınız başarıyla gönderildi. En kısa sürede size dönüş yapacağız.', 'success')
        return redirect(url_for('main.contact'))
    
    return render_template('contact.html')

@main_bp.route('/cart')
def view_cart():
    cart = get_cart()
    total = 0
    
    # Create a list of items to iterate over
    cart_items = list(cart.items())
    
    # Sepetteki ürünlerin bilgilerini güncelle
    for product_id, item in cart_items:
        product = Product.query.get(product_id)
        if product:
            # Ürün bilgilerini güncelle
            item['stock'] = product.stock
            item['price'] = float(product.price)
            # Eğer sepetteki miktar stoktan fazlaysa, stok miktarına düşür
            if item['quantity'] > product.stock:
                item['quantity'] = product.stock
            total += item['price'] * item['quantity']
        else:
            # Ürün artık yoksa sepetten kaldır
            del cart[product_id]
    
    save_cart(cart)
    return render_template('cart.html', cart=cart, total=total)

@main_bp.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))
    
    product = Product.query.get_or_404(product_id)
    
    if product.stock < quantity:
        return jsonify({
            'success': False,
            'message': 'Yeterli stok yok!'
        }), 400
    
    cart = session.get('cart', {})
    
    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += quantity
    else:
        cart[str(product_id)] = {
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'quantity': quantity,
            'image': product.image_path
        }
    
    session['cart'] = cart
    
    return jsonify({
        'success': True,
        'cart_count': sum(item['quantity'] for item in cart.values())
    })

@main_bp.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    data = request.get_json()
    product_id = str(data.get('product_id'))
    quantity = int(data.get('quantity', 1))
    
    cart = session.get('cart', {})
    
    if product_id in cart:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({
                'success': False,
                'message': 'Ürün bulunamadı!'
            }), 404
            
        # Güncel stok kontrolü
        if quantity <= 0:
            return jsonify({
                'success': False,
                'message': 'Miktar 0\'dan büyük olmalıdır!'
            }), 400
            
        if product.stock < quantity:
            return jsonify({
                'success': False,
                'message': f'Stokta sadece {product.stock} adet ürün bulunuyor!',
                'max_stock': product.stock
            }), 400
            
        cart[product_id]['quantity'] = quantity
        cart[product_id]['stock'] = product.stock  # Stok bilgisini güncelle
        session['cart'] = cart
        
        # Güncel toplamları hesapla
        total = sum(item['price'] * item['quantity'] for item in cart.values())
        tax = total * 0.18
        grand_total = total + tax
        
        return jsonify({
            'success': True,
            'totals': {
                'subtotal': float(total),
                'tax': float(tax),
                'grand_total': float(grand_total)
            }
        })
    
    return jsonify({
        'success': False,
        'message': 'Ürün sepette bulunamadı!'
    }), 404

@main_bp.route('/cart/remove', methods=['POST'])
@login_required
def remove_from_cart():
    data = request.get_json()
    if not data or 'product_id' not in data:
        return jsonify({'success': False, 'message': 'Geçersiz istek'}), 400
        
    product_id = str(data['product_id'])
    cart = session.get('cart', {})
    
    if product_id in cart:
        del cart[product_id]
        session['cart'] = cart
        return jsonify({'success': True, 'cart_count': len(cart)})
    
    return jsonify({'success': False, 'message': 'Ürün sepette bulunamadı'}), 404

@main_bp.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    session.pop('cart', None)
    return jsonify({'success': True})

@main_bp.route('/cart/total')
@login_required
def get_cart_total():
    cart = session.get('cart', {})
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    return jsonify({
        'total': f"₺{total:,.2f}",
        'raw_total': float(total)
    })

@main_bp.route('/search')
def search():
    query = request.args.get('q', '')
    category_id = request.args.get('category', type=int)
    
    products_query = Product.query
    
    if query:
        products_query = products_query.filter(
            or_(
                Product.name.ilike(f'%{query}%'),
                Product.description.ilike(f'%{query}%')
            )
        )
    
    if category_id:
        products_query = products_query.filter_by(category_id=category_id)
    
    products = products_query.order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    
    return render_template('search.html',
                         products=products,
                         categories=categories,
                         query=query,
                         selected_category=category_id)

@main_bp.context_processor
def inject_categories():
    """Her template'e kategorileri ekler."""
    categories = Category.query.order_by(Category.name).all()
    return dict(categories=categories)

@main_bp.context_processor
def inject_cart_count():
    """Her template'e sepet sayısını ekler."""
    cart = get_cart()
    cart_count = sum(item['quantity'] for item in cart.values())
    return dict(cart_count=cart_count) 

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )
        db.session.add(user)
        db.session.commit()
        
        # Yeni kullanıcı bildirimi oluştur
        create_user_notification(user)
        
        flash('Kayıt başarılı! Şimdi giriş yapabilirsiniz.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@main_bp.route('/checkout')
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Sepetiniz boş.', 'warning')
        return redirect(url_for('main.cart'))
    
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('checkout.html', cart=cart, total=total)

@main_bp.route('/address/add', methods=['POST'])
@login_required
def add_address():
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Geçersiz istek formatı'}), 400
    
    data = request.get_json()
    try:
        address = current_user.add_address(
            name=data['name'],
            full_address=data['full_address'],
            city=data['city'],
            postal_code=data['postal_code'],
            phone=data['phone'],
            is_default=data.get('is_default', False)
        )
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Adres başarıyla eklendi',
            'address': {
                'id': address.id,
                'name': address.name,
                'full_address': address.full_address,
                'city': address.city,
                'postal_code': address.postal_code,
                'phone': address.phone,
                'is_default': address.is_default
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@main_bp.route('/credit-card/add', methods=['POST'])
@login_required
def add_credit_card():
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Geçersiz istek formatı'}), 400
    
    data = request.get_json()
    try:
        card_number = data['card_number']
        
        card = current_user.add_credit_card(
            name=data['name'],
            card_number=card_number,
            card_holder=data['card_holder'],
            expiry_month=data['expiry_month'],
            expiry_year=data['expiry_year'],
            cvv=data['cvv'],  # CVV parametresini ekle
            is_default=data.get('is_default', False)
        )
        db.session.commit()
        
        masked_number = '*' * (len(card_number) - 4) + card_number[-4:]
        return jsonify({
            'success': True,
            'message': 'Kredi kartı başarıyla eklendi',
            'card': {
                'id': card.id,
                'name': card.name,
                'card_number': masked_number,
                'card_holder': card.card_holder,
                'expiry_month': card.expiry_month,
                'expiry_year': card.expiry_year,
                'is_default': card.is_default
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@main_bp.route('/credit-card/delete/<int:card_id>', methods=['POST'])
@login_required
def delete_credit_card(card_id):
    card = CreditCard.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Yetkisiz işlem'}), 403
    try:
        db.session.delete(card)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@main_bp.route('/order/create', methods=['POST'])
@login_required
def create_order():
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Geçersiz istek formatı'}), 400
    
    data = request.get_json()
    cart = session.get('cart', {})
    
    if not cart:
        return jsonify({'success': False, 'message': 'Sepetiniz boş'}), 400
    
    try:
        # Adres ve kredi kartı kontrolü
        address = Address.query.get(data['address_id'])
        credit_card = CreditCard.query.get(data['credit_card_id'])
        
        if not address or address.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Geçersiz adres'}), 400
        
        if not credit_card or credit_card.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Geçersiz kredi kartı'}), 400
        
        # Sipariş oluştur
        order = Order(
            user_id=current_user.id,
            address_id=address.id,
            credit_card_id=credit_card.id,
            status='pending',
            total_amount=sum(item['price'] * item['quantity'] for item in cart.values()) * 1.18  # KDV dahil
        )
        db.session.add(order)
        
        # Sipariş detaylarını ekle
        for product_id, item in cart.items():
            product = Product.query.get(product_id)
            if not product or product.stock < item['quantity']:
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'message': f'{product.name if product else "Ürün"} için yeterli stok yok'
                }), 400
            
            order_item = OrderItem(
                order=order,
                product_id=product_id,
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(order_item)
            
            # Stok güncelle
            product.stock -= item['quantity']
        
        db.session.commit()
        
        # Sepeti temizle
        session.pop('cart', None)
        
        return jsonify({
            'success': True,
            'message': 'Sipariş başarıyla oluşturuldu',
            'order_id': order.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@main_bp.route('/order/confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
        
    # Sipariş durumunu güncelle
    if order.status == 'pending':
        try:
            order.status = 'processing'
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('Sipariş işlenirken bir hata oluştu.', 'error')
            return redirect(url_for('main.profile'))
            
    return render_template('order_confirmation.html', order=order)

@main_bp.route('/orders')
@login_required
def view_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)

@main_bp.route('/profile')
@login_required
def profile():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(3).all()
    return render_template('profile.html', user=current_user, orders=orders)

@main_bp.route('/address/delete/<int:address_id>', methods=['POST'])
@login_required
def delete_address(address_id):
    address = Address.query.get_or_404(address_id)
    if address.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Yetkisiz işlem'}), 403
    try:
        db.session.delete(address)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@main_bp.route('/product/<int:product_id>/review', methods=['POST'])
@login_required
def add_review(product_id):
    product = Product.query.get_or_404(product_id)
    
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Geçersiz istek formatı'}), 400
    
    data = request.get_json()
    rating = data.get('rating')
    content = data.get('comment', '').strip()
    
    if not rating or not isinstance(rating, (int, float)) or rating < 1 or rating > 5:
        return jsonify({'success': False, 'message': 'Geçerli bir puan giriniz (1-5)'}), 400
    
    try:
        # Kullanıcının daha önce yorum yapıp yapmadığını kontrol et
        existing_review = Review.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if existing_review:
            # Mevcut yorumu güncelle
            existing_review.rating = rating
            existing_review.content = content
            existing_review.updated_at = datetime.utcnow()
        else:
            # Yeni yorum ekle
            review = Review(
                user_id=current_user.id,
                product_id=product_id,
                rating=rating,
                content=content
            )
            db.session.add(review)
        
        db.session.commit()
        
        # Ürünün ortalama puanını güncelle
        Review.update_product_rating(product_id)
        
        return jsonify({
            'success': True,
            'message': 'Yorumunuz başarıyla kaydedildi',
            'review': {
                'rating': rating,
                'content': content,
                'username': current_user.username,
                'created_at': datetime.utcnow().strftime('%d.%m.%Y %H:%M')
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@main_bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Siparişin kullanıcıya ait olup olmadığını kontrol et
    if order.user_id != current_user.id:
        flash('Bu siparişi görüntüleme yetkiniz yok.', 'error')
        return redirect(url_for('main.profile'))
    
    return render_template('order_detail.html', order=order, Decimal=Decimal)

# Admin routes
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
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@admin_bp.route('/order/<int:order_id>')
@login_required
@admin_required
def order_details(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_details.html', order=order)

@admin_bp.route('/order/update-status', methods=['POST'])
@login_required
@admin_required
def update_order_status():
    order_id = request.form.get('order_id')
    new_status = request.form.get('status')
    
    if not order_id or not new_status:
        return jsonify({'success': False, 'message': 'Geçersiz istek'}), 400
    
    order = Order.query.get_or_404(order_id)
    
    try:
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
        return jsonify({'success': False, 'message': str(e)}), 400 