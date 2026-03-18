from app import create_app
from extensions import db
from models import Product, User

def seed():
    app = create_app()
    with app.app_context():
        samples = [
            {'barcode': '1001', 'name': 'Milk 1L', 'price': 60.0, 'purchase_price': 50.0, 'gst_rate': 5.0, 'stock_quantity': 50, 'hsn_code': '0401'},
            {'barcode': '1002', 'name': 'Bread 400g', 'price': 40.0, 'purchase_price': 30.0, 'gst_rate': 0.0, 'stock_quantity': 30, 'hsn_code': '1905'},
            {'barcode': '1003', 'name': 'Dark Chocolate', 'price': 150.0, 'purchase_price': 100.0, 'gst_rate': 18.0, 'stock_quantity': 100, 'hsn_code': '1806'},
            {'barcode': '1004', 'name': 'Mineral Water 1L', 'price': 20.0, 'purchase_price': 12.0, 'gst_rate': 18.0, 'stock_quantity': 200, 'hsn_code': '2201'},
            {'barcode': '1005', 'name': 'Soap Bar', 'price': 45.0, 'purchase_price': 30.0, 'gst_rate': 18.0, 'stock_quantity': 5, 'hsn_code': '3401'}
        ]
        
        for s in samples:
            if not Product.query.filter_by(barcode=s['barcode']).first():
                p = Product(**s)
                db.session.add(p)
        
        db.session.commit()
        print("Database seeded with sample products!")

if __name__ == '__main__':
    seed()
