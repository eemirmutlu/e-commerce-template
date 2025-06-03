from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, FloatField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo, Optional, NumberRange, ValidationError, Email
from flask_wtf.file import FileField, FileAllowed
from app.models import User

class LoginForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[DataRequired()])
    password = PasswordField('Şifre', validators=[DataRequired()])
    remember_me = BooleanField('Beni Hatırla')
    submit = SubmitField('Giriş Yap')

class RegisterForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[
        DataRequired(),
        Length(min=3, max=20, message='Kullanıcı adı 3-20 karakter arasında olmalıdır.')
    ])
    email = StringField('E-posta', validators=[
        DataRequired(),
        Email(message='Geçerli bir e-posta adresi giriniz.')
    ])
    password = PasswordField('Şifre', validators=[
        DataRequired(),
        Length(min=6, message='Şifre en az 6 karakter olmalıdır.')
    ])
    password2 = PasswordField('Şifre Tekrar', validators=[
        DataRequired(),
        EqualTo('password', message='Şifreler eşleşmiyor.')
    ])
    submit = SubmitField('Kayıt Ol')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Bu kullanıcı adı zaten kullanılıyor.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Bu e-posta adresi zaten kullanılıyor.')

class ProductForm(FlaskForm):
    name = StringField('Ürün Adı', validators=[
        DataRequired(message='Ürün adı zorunludur.'),
        Length(min=3, max=100, message='Ürün adı 3-100 karakter arasında olmalıdır.')
    ])
    
    description = TextAreaField('Açıklama', validators=[
        DataRequired(message='Ürün açıklaması zorunludur.'),
        Length(min=10, message='Açıklama en az 10 karakter olmalıdır.')
    ])
    
    price = FloatField('Fiyat', validators=[
        DataRequired(message='Fiyat zorunludur.'),
        NumberRange(min=0, message='Fiyat 0\'dan büyük olmalıdır.')
    ])
    
    stock = IntegerField('Stok', validators=[
        DataRequired(message='Stok miktarı zorunludur.'),
        NumberRange(min=0, message='Stok miktarı 0\'dan küçük olamaz.')
    ])
    
    category_id = SelectField('Kategori', coerce=int, validators=[
        DataRequired(message='Kategori seçimi zorunludur.')
    ])
    
    image = FileField('Ürün Resmi', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Sadece resim dosyaları yüklenebilir!')
    ])
    
    is_active = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')

class CategoryForm(FlaskForm):
    name = StringField('Kategori Adı', validators=[
        DataRequired(message='Kategori adı zorunludur.'),
        Length(min=2, max=100, message='Kategori adı 2-100 karakter arasında olmalıdır.')
    ])
    
    description = TextAreaField('Açıklama', validators=[
        Optional(),
        Length(max=500, message='Açıklama en fazla 500 karakter olabilir.')
    ])
    
    icon = StringField('İkon', validators=[
        Optional(),
        Length(max=50, message='İkon adı en fazla 50 karakter olabilir.')
    ])
    
    color = StringField('Renk', validators=[
        Optional(),
        Length(max=7, message='Geçerli bir renk kodu giriniz (örn: #FF0000).')
    ])
    
    is_active = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')

class NewsForm(FlaskForm):
    title = StringField('Başlık', validators=[
        DataRequired(message='Haber başlığı zorunludur.'),
        Length(min=5, max=200, message='Başlık 5-200 karakter arasında olmalıdır.')
    ])
    
    summary = TextAreaField('Özet', validators=[
        Optional(),
        Length(max=500, message='Özet en fazla 500 karakter olabilir.')
    ])
    
    content = TextAreaField('İçerik', validators=[
        DataRequired(message='Haber içeriği zorunludur.'),
        Length(min=50, message='İçerik en az 50 karakter olmalıdır.')
    ])
    
    image = FileField('Haber Resmi', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Sadece resim dosyaları yüklenebilir!')
    ])
    
    image_url = StringField('Mevcut Resim', validators=[Optional()])
    
    is_published = BooleanField('Yayınla', default=False)
    submit = SubmitField('Kaydet')

    def validate_image(self, field):
        if field.data and field.data.filename:
            # Dosya boyutu kontrolü (2MB)
            if len(field.data.read()) > 2 * 1024 * 1024:
                raise ValidationError('Dosya boyutu 2MB\'dan büyük olamaz.')
            field.data.seek(0)  # Dosya pointer'ı başa al

class ContactForm(FlaskForm):
    name = StringField('Adınız', validators=[
        DataRequired(message='Adınızı girmeniz zorunludur.'),
        Length(min=2, max=50, message='Adınız 2-50 karakter arasında olmalıdır.')
    ])
    
    email = StringField('E-posta', validators=[
        DataRequired(message='E-posta adresinizi girmeniz zorunludur.'),
        Email(message='Geçerli bir e-posta adresi giriniz.')
    ])
    
    subject = StringField('Konu', validators=[
        DataRequired(message='Konu girmeniz zorunludur.'),
        Length(min=3, max=100, message='Konu 3-100 karakter arasında olmalıdır.')
    ])
    
    message = TextAreaField('Mesajınız', validators=[
        DataRequired(message='Mesajınızı girmeniz zorunludur.'),
        Length(min=10, max=1000, message='Mesajınız 10-1000 karakter arasında olmalıdır.')
    ])
    
    submit = SubmitField('Gönder') 