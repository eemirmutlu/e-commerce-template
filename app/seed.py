from app import db, create_app
from app.models import User

def seed_admin():
    app = create_app()
    with app.app_context():
        # Önce mevcut admin kullanıcısını sil
        User.query.filter(
            (User.username == 'admin') | (User.email == 'admin@techstore.com')
        ).delete()
        db.session.commit()
        
        # Yeni admin kullanıcısı oluştur
        admin = User(
            username='admin',
            email='admin@techstore.com',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        try:
            db.session.commit()
            print('Admin kullanıcısı başarıyla oluşturuldu!')
            print('E-posta: admin@techstore.com')
            print('Şifre: admin123')
        except Exception as e:
            db.session.rollback()
            print(f'Hata oluştu: {str(e)}')

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_admin()
        print('Veritabanı başarıyla dolduruldu!') 