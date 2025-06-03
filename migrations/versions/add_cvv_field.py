"""Add CVV field to credit cards

Revision ID: add_cvv_field
Revises: cde96cf870be
Create Date: 2024-03-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'add_cvv_field'
down_revision = 'cde96cf870be'
branch_labels = None
depends_on = None

def upgrade():
    # SQLite'da mevcut verileri koruyarak sütun eklemek için
    # önce geçici bir tablo oluşturup, verileri oraya taşıyacağız
    conn = op.get_bind()
    
    # 1. Yeni sütunlu geçici tablo oluştur
    conn.execute(text("""
        CREATE TABLE credit_cards_new (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            card_number VARCHAR(19) NOT NULL,
            card_holder VARCHAR(100) NOT NULL,
            expiry_month INTEGER NOT NULL,
            expiry_year INTEGER NOT NULL,
            cvv VARCHAR(4) NOT NULL DEFAULT '000',
            is_default BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """))
    
    # 2. Mevcut verileri yeni tabloya kopyala
    conn.execute(text("""
        INSERT INTO credit_cards_new (
            id, user_id, name, card_number, card_holder, 
            expiry_month, expiry_year, is_default, created_at, updated_at
        )
        SELECT 
            id, user_id, name, card_number, card_holder,
            expiry_month, expiry_year, is_default, created_at, updated_at
        FROM credit_cards
    """))
    
    # 3. Eski tabloyu sil
    conn.execute(text("DROP TABLE credit_cards"))
    
    # 4. Yeni tabloyu eski isimle yeniden adlandır
    conn.execute(text("ALTER TABLE credit_cards_new RENAME TO credit_cards"))
    
    # 5. İndeksleri yeniden oluştur
    conn.execute(text("CREATE INDEX ix_credit_cards_user_id ON credit_cards (user_id)"))

def downgrade():
    # Benzer şekilde geri alma işlemi
    conn = op.get_bind()
    
    # 1. Eski yapıda geçici tablo oluştur
    conn.execute(text("""
        CREATE TABLE credit_cards_old (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            card_number VARCHAR(19) NOT NULL,
            card_holder VARCHAR(100) NOT NULL,
            expiry_month INTEGER NOT NULL,
            expiry_year INTEGER NOT NULL,
            is_default BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """))
    
    # 2. Verileri geri kopyala (CVV hariç)
    conn.execute(text("""
        INSERT INTO credit_cards_old (
            id, user_id, name, card_number, card_holder,
            expiry_month, expiry_year, is_default, created_at, updated_at
        )
        SELECT 
            id, user_id, name, card_number, card_holder,
            expiry_month, expiry_year, is_default, created_at, updated_at
        FROM credit_cards
    """))
    
    # 3. Yeni tabloyu sil
    conn.execute(text("DROP TABLE credit_cards"))
    
    # 4. Eski tabloyu orijinal isimle yeniden adlandır
    conn.execute(text("ALTER TABLE credit_cards_old RENAME TO credit_cards"))
    
    # 5. İndeksleri yeniden oluştur
    conn.execute(text("CREATE INDEX ix_credit_cards_user_id ON credit_cards (user_id)")) 