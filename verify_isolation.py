import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app import create_app
from extensions import db
from models import User, Product, Customer, BusinessSettings, Shift

app = create_app()

def test_isolation():
    with app.app_context():
        print("Starting Isolation Test (No Categories)...")
        
        # Cleanup potential old test users
        User.query.filter(User.username.like('testuser%')).delete()
        db.session.commit()
        
        # 1. Create User A
        user_a = User(username='testuser_a', is_approved=True)
        user_a.set_password('pass123')
        db.session.add(user_a)
        db.session.flush()
        
        # 2. Create User B
        user_b = User(username='testuser_b', is_approved=True)
        user_b.set_password('pass123')
        db.session.add(user_b)
        db.session.flush()
        
        # 3. Add data for User A
        prod_a = Product(barcode='12345', name='Prod A', price=10.0, user_id=user_a.id)
        db.session.add(prod_a)
        
        cust_a = Customer(name='Cust A', phone='11111', user_id=user_a.id)
        db.session.add(cust_a)
        
        db.session.commit()
        print(f"User A ({user_a.id}) data created.")

        # 4. Verify User B can NOT see User A's data
        print("Verifying User B isolation...")
        
        prods_b = Product.query.filter_by(user_id=user_b.id).all()
        custs_b = Customer.query.filter_by(user_id=user_b.id).all()
        shifts_b = Shift.query.filter_by(user_id=user_b.id).all()
        
        assert len(prods_b) == 0, f"Expected 0 products for B, found {len(prods_b)}"
        assert len(custs_b) == 0, f"Expected 0 customers for B, found {len(custs_b)}"
        assert len(shifts_b) == 0, f"Expected 0 shifts for B, found {len(shifts_b)}"
        
        print("User B isolation verified: All counts are 0.")
        
        # Cleanup
        db.session.delete(user_a)
        db.session.delete(user_b)
        db.session.commit()
        print("Isolation Test Passed!")

if __name__ == '__main__':
    try:
        test_isolation()
    except Exception as e:
        print(f"Test Failed: {e}")
        sys.exit(1)
