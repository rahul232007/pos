from app import create_app
from extensions import db
from models import Product
import random

def seed_data():
    app = create_app()
    with app.app_context():
        print("Adding Hundreds of Grocery Items (No Categories)...")
        
        products = [
            # Dairy
            ('Whole Milk 1L',  60.0, '8901058000010', 5),
            ('Low Fat Milk 1L',  65.0, '8901058000027', 5),
            ('Salted Butter 100g',  52.0, '8901058000034', 12),
            ('Cheese Slices 200g',  140.0, '8901058000041', 12),
            ('Greek Yogurt 400g',  120.0, '8901058000058', 5),
            ('Fresh Paneer 200g',  85.0, '8901058000065', 5),
            ('Large Eggs 6pk',  45.0, '8901058000072', 0),
            
            # Bakery
            ('White Bread 400g',  40.0, '8901058000102', 0),
            ('Brown Bread 400g',  50.0, '8901058000119', 0),
            ('Chocolate Muffins 4pk',  120.0, '8901058000126', 18),
            ('Marie Biscuits 200g',  30.0, '8901058000133', 18),
            ('Chocolate Croissant',  60.0, '8901058000140', 18),
            
            # Produce
            ('Apples 1kg',  180.0, '8901058000201', 0),
            ('Bananas 1dz',  60.0, '8901058000218', 0),
            ('Potatoes 1kg',  30.0, '8901058000225', 0),
            ('Onions 1kg',  40.0, '8901058000232', 0),
            ('Tomatoes 1kg',  50.0, '8901058000249', 0),
            
            # Snacks
            ('Potato Chips Classic',  20.0, '8901058000300', 12),
            ('Nachos Cheese 150g',  90.0, '8901058000317', 12),
            ('Chocolate Bar 50g',  40.0, '8901058000324', 18),
            ('Roasted Almonds 200g',  250.0, '8901058000331', 12),
            ('Instant Noodles 70g',  12.0, '8901058000348', 12),
            
            # Beverages
            ('Cola 500ml',  40.0, '8901058000409', 28),
            ('Orange Juice 1L',  110.0, '8901058000416', 12),
            ('Mineral Water 1L',  20.0, '8901058000423', 18),
            ('Energy Drink 250ml',  125.0, '8901058000430', 28),
            ('Instant Coffee 50g',  180.0, '8901058000447', 18),
            
            # Household
            ('Dishwashing Liquid 500ml',  105.0, '8901058000508', 18),
            ('Laundry Detergent 1kg',  210.0, '8901058000515', 18),
            ('Toilet Cleaner 500ml',  95.0, '8901058000522', 18),
            ('Kitchen Towels 2pk',  80.0, '8901058000539', 12),
            ('Floor Cleaner 1L',  150.0, '8901058000546', 18),
            
            # Personal Care
            ('Bath Soap 125g',  45.0, '8901058000607', 18),
            ('Hand Wash 250ml',  90.0, '8901058000614', 18),
            ('Shampoo 180ml',  160.0, '8901058000621', 18),
            ('Toothpaste 150g',  85.0, '8901058000638', 18),
            ('Moisturizer 200ml',  250.0, '8901058000645', 18)
        ]

        # Generate more bulk items
        for i in range(100):
            barcode = f"8902000{i:06d}"
            name = f"Generic Item {i+1}"
            price = round(random.uniform(10, 500), 2)
            gst = random.choice([0, 5, 12, 18])
            products.append((name, price, barcode, gst))

        for name, price, barcode, gst in products:
            existing = Product.query.filter_by(barcode=barcode).first()
            if not existing:
                p = Product(
                    name=name,
                    price=price,
                    barcode=barcode,
                    gst_rate=gst,
                    stock_quantity=random.randint(50, 200)
                )
                db.session.add(p)
        
        db.session.commit()
        print(f"Successfully added/verified {len(products)} products.")

if __name__ == '__main__':
    seed_data()
