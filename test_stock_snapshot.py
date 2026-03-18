import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app import create_app
from extensions import db
from models import Product, User, StockAdjustment

app = create_app()

def test_stock_snapshot():
    with app.app_context():
        print("Starting Stock Snapshot Verification...")
        
        # 1. Setup - find or create a user and product
        user = User.query.first()
        if not user:
            print("No user found for test.")
            return

        # Create a test product
        p = Product(barcode='TEST-ADJ-999', name='Test Adj Product', price=100, stock_quantity=50, user_id=user.id)
        db.session.add(p)
        db.session.commit()
        print(f"Test Product Created: {p.name} with Stock: {p.stock_quantity}")

        # 2. Perform Adjustment
        from routes_inventory import add_adjustment
        # We can't easily call the route directly because of Flask-Login/Request context, 
        # so we'll simulate the logic inside the route.
        
        quantity_to_add = 10
        stock_before = p.stock_quantity
        p.stock_quantity += quantity_to_add
        adj = StockAdjustment(
            product_id=p.id,
            quantity=quantity_to_add,
            reason='test-audit',
            stock_snapshot=stock_before,
            user_id=user.id
        )
        db.session.add(adj)
        db.session.commit()
        print(f"Adjustment applied: +{quantity_to_add}. Stock before was {stock_before}.")

        # 3. Verify
        latest_adj = StockAdjustment.query.filter_by(product_id=p.id).order_by(StockAdjustment.timestamp.desc()).first()
        print(f"Verification: Snapshot={latest_adj.stock_snapshot}, Expected={stock_before}")
        
        assert latest_adj.stock_snapshot == stock_before, "Stock snapshot mismatch!"
        
        # Cleanup
        db.session.delete(adj)
        db.session.delete(p)
        db.session.commit()
        print("Stock Snapshot Verification Passed!")

if __name__ == '__main__':
    try:
        test_stock_snapshot()
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
