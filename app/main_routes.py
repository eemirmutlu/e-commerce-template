from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app.models import Product, Category, Order, OrderItem, Review, Address, CreditCard
from app import db
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/products')
def products():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    category_id = request.args.get('category_id', type=int)
    sort = request.args.get('sort', 'newest')
    search = request.args.get('search', '')
    
    query = Product.query
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort == 'name_asc':
        query = query.order_by(Product.name.asc())
    elif sort == 'name_desc':
        query = query.order_by(Product.name.desc())
    else:  # newest
        query = query.order_by(Product.created_at.desc())
    
    products = query.paginate(page=page, per_page=per_page)
    categories = Category.query.all()
    
    return render_template('products.html',
        products=products,
        categories=categories,
        current_category=category_id,
        current_sort=sort,
        current_search=search
    ) 