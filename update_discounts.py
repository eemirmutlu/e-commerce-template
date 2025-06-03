from app import create_app, db
from app.models import Product

app = create_app()
with app.app_context():
    # NULL değerleri 0 ile güncelle
    Product.query.filter(Product.discount_percent.is_(None)).update({Product.discount_percent: 0})
    db.session.commit()
    print("Discount percentages updated successfully!") 