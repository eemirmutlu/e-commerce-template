from app import create_app, db
from app.models import User

def reset_admin():
    app = create_app()
    with app.app_context():
        # Mevcut admin kullanıcısını sil
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
            
            # Kontrol et
            admin = User.query.filter_by(email='admin@techstore.com').first()
            if admin and admin.check_password('admin123'):
                print('Şifre kontrolü başarılı!')
            else:
                print('Şifre kontrolü başarısız!')
        except Exception as e:
            db.session.rollback()
            print(f'Hata oluştu: {str(e)}')

if __name__ == '__main__':
    reset_admin() 