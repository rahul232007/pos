from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100))
    company_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    mobile = db.Column(db.String(20))
    country_code = db.Column(db.String(10), default='+91')
    otp_code = db.Column(db.String(6))
    is_verified = db.Column(db.Boolean, default=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='cashier') # 'admin' or 'cashier'
    is_approved = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    hsn_code = db.Column(db.String(20))
    price = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, default=0.0)
    gst_rate = db.Column(db.Float, default=18.0)
    stock_quantity = db.Column(db.Integer, default=0)
    unit = db.Column(db.String(20), default='pcs') # pcs, kg, ltr, etc.
    expiry_date = db.Column(db.Date, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    variants = db.relationship('ProductVariant', backref='product', lazy=True)
    modifiers = db.relationship('ProductModifier', secondary='product_modifier_links')

class ProductVariant(db.Model):
    __tablename__ = 'product_variants'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False) # e.g., 'Small', 'Blue'
    price_impact = db.Column(db.Float, default=0.0)
    stock_quantity = db.Column(db.Integer, default=0)

class ProductModifier(db.Model):
    __tablename__ = 'product_modifiers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False) # e.g., 'Extra Cheese'
    price = db.Column(db.Float, default=0.0)

db.Table('product_modifier_links',
    db.Column('product_id', db.Integer, db.ForeignKey('products.id')),
    db.Column('modifier_id', db.Integer, db.ForeignKey('product_modifiers.id'))
)

class Shift(db.Model):
    __tablename__ = 'shifts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    opening_cash = db.Column(db.Float, default=0.0)
    closing_cash = db.Column(db.Float)
    actual_cash = db.Column(db.Float) # Counted by staff
    status = db.Column(db.String(20), default='open') # 'open', 'closed'

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True)
    email = db.Column(db.String(100))
    loyalty_points = db.Column(db.Integer, default=0)
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    invoices = db.relationship('Invoice', backref='customer', lazy=True)

class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    customer_gstin = db.Column(db.String(15), nullable=True)
    payment_mode = db.Column(db.String(20), default='Cash') # Cash, UPI, Card, Mixed
    total_amount = db.Column(db.Float, nullable=False)
    total_gst = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='completed') # 'completed', 'returned', 'draft'
    payment_status = db.Column(db.String(20), default='paid') # 'paid', 'pending', 'failed'
    payment_link = db.Column(db.String(255), nullable=True) # URL for payment tracking
    cashier_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.id'), nullable=True)
    
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True)

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variants.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    gst_amount = db.Column(db.Float, nullable=False)
    modifiers_json = db.Column(db.Text) # Storing selected modifiers as stringified JSON
    
    product = db.relationship('Product')
    variant = db.relationship('ProductVariant')

class BusinessSettings(db.Model):
    __tablename__ = 'business_settings'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), default='Quantum POS')
    gstin = db.Column(db.String(15), default='GSTIN-PENDING')
    address = db.Column(db.Text, default='Our Store Address, City, State')
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100))
    receipt_footer = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

class StockAdjustment(db.Model):
    __tablename__ = 'stock_adjustments'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variants.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False) # e.g., -5 for damage, +10 for stocktake
    reason = db.Column(db.String(100)) # 'damage', 'loss', 'manual_count'
    stock_snapshot = db.Column(db.Integer) # Record stock at the time of adjustment
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    product = db.relationship('Product')
    user = db.relationship('User')
