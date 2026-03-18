import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app import create_app
from extensions import db
from models import Product

app = create_app()

def test_sanity():
    with app.app_context():
        print("Checking application sanity...")
        # Check if we can query products (Category relation removal check)
        try:
            p = Product.query.first()
            print(f"Product query successful. {p.name if p else 'No products'}")
        except Exception as e:
            print(f"Product query failed: {e}")
            sys.exit(1)
            
        print("Sanity Check Passed!")

if __name__ == '__main__':
    test_sanity()
