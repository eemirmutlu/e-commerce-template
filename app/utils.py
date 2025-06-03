from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    """
    Admin yetkisi gerektiren route'lar için decorator.
    Kullanıcının giriş yapmış ve admin yetkisine sahip olmasını kontrol eder.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def format_currency(value):
    """
    Para birimini formatlar (örn: 1234.56 -> 1.234,56 ₺)
    """
    try:
        return f"{float(value):,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "0,00 ₺"

def slugify(text):
    """
    Metni URL-dostu bir slug'a dönüştürür.
    """
    import re
    import unicodedata
    
    # Türkçe karakterleri değiştir
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u')
    text = text.replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = text.replace('İ', 'I').replace('Ğ', 'G').replace('Ü', 'U')
    text = text.replace('Ş', 'S').replace('Ö', 'O').replace('Ç', 'C')
    
    # Unicode'u normalize et
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    
    # Küçük harfe çevir ve alfanumerik olmayan karakterleri tire ile değiştir
    text = re.sub(r'[^a-z0-9]+', '-', text.lower())
    
    # Baştaki ve sondaki tireleri kaldır
    text = text.strip('-')
    
    return text

def get_file_extension(filename):
    """
    Dosya adından uzantıyı döndürür.
    """
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def is_allowed_file(filename, allowed_extensions=None):
    """
    Dosya uzantısının izin verilen türlerden olup olmadığını kontrol eder.
    """
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return get_file_extension(filename) in allowed_extensions

def generate_unique_filename(filename):
    """
    Benzersiz bir dosya adı oluşturur.
    """
    from datetime import datetime
    import uuid
    
    ext = get_file_extension(filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    
    return f"{timestamp}_{unique_id}.{ext}" 