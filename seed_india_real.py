from app import create_app
from extensions import db
from models import Product, Invoice, InvoiceItem
import random

def seed_real_india():
    app = create_app()
    with app.app_context():
        print("Cleaning up old data...")
        db.session.query(InvoiceItem).delete()
        db.session.query(Invoice).delete()
        db.session.query(Product).delete()
        db.session.commit()

        print("Adding Authentic Indian Products (No Categories)...")
        
        # Real Product Data (Product Name, Price, Barcode, GST)
        products = [
            # --- STAPLES ---
            ('Aashirvaad Whole Wheat Atta 1kg',  65.0, '8901725016838', 0),
            ('Aashirvaad Whole Wheat Atta 5kg',  285.0, '8901725001650', 0),
            ('Aashirvaad Whole Wheat Atta 10kg',  540.0, '8909081004568', 0),
            ('Tata Salt 1kg',  28.0, '8904043901015', 0),
            ('Tata Salt Lite 1kg',  45.0, '8904043901077', 0),
            ('Tata Himalayan Rock Salt 1kg',  110.0, '8904043907642', 0),

            # --- DAIRY ---
            ('Amul Fresh Cream 1L',  220.0, '8901262010160', 5), 
            ('Amul Pure Ghee 1L Pouch',  630.0, '8901262030151', 12),
            ('Amul Cow Ghee 1L Tin',  650.0, '8901262030694', 12),
            ('Amul Butter 100g',  56.0, '8901262010016', 12),
            ('Amul Butter 500g',  275.0, '8901262010023', 12),
            ('Amul Cheese Slices 200g',  155.0, '8901262060011', 12),
            ('Amul Dahi 200g',  22.0, '8901262200271', 5),

            # --- BISCUITS & SNACKS ---
            ('Britannia Marie Gold 250g',  35.0, '8901063023901', 18),
            ('Britannia Good Day Butter 100g',  20.0, '8901063092099', 18),
            ('Britannia Good Day Cashew 90g',  25.0, '8901063136069', 18),
            ('Britannia Little Hearts 75g',  20.0, '8901063019089', 18),
            ('Britannia 50-50 Maska Chaska 120g',  35.0, '8901063017221', 18),
            ('Britannia Bourbon 100g',  30.0, '8901063030022', 18),

            # --- NOODLES & INSTANT FOOD ---
            ('Maggi Masala Noodles 70g',  14.0, '8901058000290', 12),
            ('Maggi Masala Noodles 140g',  28.0, '8901058851304', 12),
            ('Maggi Noodles Masala 280g',  56.0, '8901058851311', 12),
            ('Maggi Vegetable Atta Noodles 320g',  95.0, '8901058138054', 12),
            ('Maggi Cuppa Noodles Masala',  45.0, '8901058128819', 12),

            # --- HOME CARE ---
            ('Surf Excel Bar 84g',  10.0, '8901030875908', 18),
            ('Surf Excel Bar 250g',  30.0, '8901030865169', 18),
            ('Rin Detergent Bar 250g',  22.0, '8901030848063', 18),
            
            # --- PERSONAL CARE ---
            ('Colgate Strong Teeth 200g',  105.0, '8901314309325', 18),
            ('Dettol Original Soap 125g',  55.0, '8901399014168', 18),
            ('Clinic Plus Shampoo 175ml',  120.0, '8901030678912', 18),
            ('Lifebuoy Total Soap 125g',  40.0, '8901030112233', 18)
        ]

        seen_barcodes = set()
        count = 0
        for name, price, barcode, gst in products:
            if barcode in seen_barcodes:
                print(f"Skipping duplicate barcode: {barcode} ({name})")
                continue
            seen_barcodes.add(barcode)
            
            p = Product(
                name=name,
                price=price,
                barcode=barcode,
                gst_rate=gst,
                stock_quantity=random.randint(50, 200)
            )
            db.session.add(p)
            count += 1
        
        db.session.commit()
        print(f"Successfully populated {count} authentic Indian products.")

if __name__ == '__main__':
    seed_real_india()
