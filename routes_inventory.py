from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from models import Product, StockAdjustment, ProductVariant, ProductModifier
from extensions import db
import pandas as pd
import io
import csv
import os
from werkzeug.utils import secure_filename

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/inventory')
@login_required
def list_products():
    products = Product.query.filter_by(user_id=current_user.id).all()
    return render_template('inventory.html', products=products)


@inventory_bp.route('/inventory/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        barcode = request.form.get('barcode')
        name = request.form.get('name')
        price = float(request.form.get('price'))
        purchase_price = float(request.form.get('purchase_price', 0))
        gst_rate = float(request.form.get('gst_rate'))
        stock = int(request.form.get('stock_quantity', 0))
        hsn = request.form.get('hsn_code')
        unit = request.form.get('unit', 'pcs')

        existing = Product.query.filter_by(barcode=barcode, user_id=current_user.id).first()
        if existing:
            flash('Product with this barcode already exists!')
            return redirect(url_for('inventory.add_product'))

        # Handle Image Upload
        image_url = None
        file = request.files.get('product_image')
        if file and file.filename != '':
            filename = secure_filename(f"{barcode}_{file.filename}")
            upload_path = os.path.join('static', 'uploads', 'products')
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
            file.save(os.path.join(upload_path, filename))
            image_url = f'/static/uploads/products/{filename}'

        new_product = Product(
            barcode=barcode,
            name=name,
            price=price,
            purchase_price=purchase_price,
            gst_rate=gst_rate,
            stock_quantity=stock,
            hsn_code=hsn,
            unit=unit,
            image_url=image_url,
            user_id=current_user.id
        )
        db.session.add(new_product)
        db.session.flush() # Get ID for variants

        # Handle Variants
        variant_names = request.form.getlist('variant_names[]')
        variant_prices = request.form.getlist('variant_prices[]')
        variant_stocks = request.form.getlist('variant_stocks[]')
        for vname, vprice, vstock in zip(variant_names, variant_prices, variant_stocks):
            if vname:
                variant = ProductVariant(
                    product_id=new_product.id,
                    name=vname,
                    price_impact=float(vprice) if vprice else 0.0,
                    stock_quantity=int(vstock) if vstock else 0
                )
                db.session.add(variant)

        # Handle Modifiers
        mod_names = request.form.getlist('modifier_names[]')
        mod_prices = request.form.getlist('modifier_prices[]')
        for mname, mprice in zip(mod_names, mod_prices):
            if mname:
                modifier = ProductModifier(
                    name=mname,
                    price=float(mprice) if mprice else 0.0
                )
                db.session.add(modifier)
                db.session.flush()
                # Link modifier to product (this uses the secondary table link)
                new_product.modifiers.append(modifier)

        db.session.commit()
        flash('Product with variants and modifiers added successfully!')
        return redirect(url_for('inventory.list_products'))
    return render_template('add_product.html')

@inventory_bp.route('/inventory/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.barcode = request.form.get('barcode')
        product.name = request.form.get('name')
        product.price = float(request.form.get('price'))
        product.purchase_price = float(request.form.get('purchase_price', 0))
        product.gst_rate = float(request.form.get('gst_rate'))
        product.stock_quantity = int(request.form.get('stock_quantity', 0))
        product.hsn_code = request.form.get('hsn_code')
        product.unit = request.form.get('unit', 'pcs')

        # Handle Image Update
        file = request.files.get('product_image')
        if file and file.filename != '':
            filename = secure_filename(f"{product.barcode}_{file.filename}")
            upload_path = os.path.join('static', 'uploads', 'products')
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
            file.save(os.path.join(upload_path, filename))
            product.image_url = f'/static/uploads/products/{filename}'

        db.session.commit()
        flash('Product updated successfully!')
        return redirect(url_for('inventory.list_products'))
        
    return render_template('edit_product.html', product=product)

@inventory_bp.route('/inventory/delete/<int:product_id>')
@login_required
def delete_product(product_id):
    if current_user.role != 'admin':
        flash('Access denied.')
        return redirect(url_for('inventory.list_products'))
        
    product = Product.query.get_or_404(product_id)
    try:
        # Delete related items first if necessary, or let cascade handle it if configured
        # Since we have InvoiceItem refs, we might need to be careful
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting product: {str(e)}')
        
    return redirect(url_for('inventory.list_products'))


@inventory_bp.route('/inventory/upload', methods=['POST'])
@login_required
def upload_excel():
    file = request.files.get('file')
    if file and file.filename.endswith(('.xlsx', '.xls', '.csv')):
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            count = 0
            for _, row in df.iterrows():
                # Check for required columns
                if not Product.query.filter_by(barcode=str(row['barcode']), user_id=current_user.id).first():
                    product = Product(
                        barcode=str(row['barcode']),
                        name=row['name'],
                        price=float(row['price']),
                        purchase_price=float(row.get('purchase_price', 0)),
                        gst_rate=float(row.get('gst_rate', 18)),
                        stock_quantity=int(row.get('stock_quantity', 0)),
                        unit=str(row.get('unit', 'pcs')),
                        hsn_code=str(row.get('hsn_code', '')),
                        user_id=current_user.id
                    )
                    db.session.add(product)
                    count += 1
            
            db.session.commit()
            flash(f'{count} products uploaded successfully!')
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading file: {str(e)}')
    else:
        flash('Please upload a valid Excel or CSV file.')
    return redirect(url_for('inventory.list_products'))

@inventory_bp.route('/inventory/export')
@login_required
def export_inventory():
    products = Product.query.filter_by(user_id=current_user.id).all()
    
    def generate():
        data = io.StringIO()
        writer = csv.writer(data)
        writer.writerow(['barcode', 'name', 'price', 'gst_rate', 'stock_quantity', 'unit', 'hsn_code'])
        yield data.getvalue()
        data.truncate(0)
        data.seek(0)
        
        for p in products:
            writer.writerow([p.barcode, p.name, p.price, p.gst_rate, p.stock_quantity, p.unit, p.hsn_code])
            yield data.getvalue()
            data.truncate(0)
            data.seek(0)

    response = Response(generate(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename="inventory.csv")
    return response

@inventory_bp.route('/inventory/adjustments')
@login_required
def list_adjustments():
    adjustments = StockAdjustment.query.join(Product).filter(Product.user_id == current_user.id).order_by(StockAdjustment.timestamp.desc()).all()
    products = Product.query.filter_by(user_id=current_user.id).all()
    return render_template('stock_adjustments.html', adjustments=adjustments, products=products)

@inventory_bp.route('/inventory/adjust', methods=['POST'])
@login_required
def add_adjustment():
    product_id = request.form.get('product_id')
    quantity_str = request.form.get('quantity', '0')
    quantity = int(quantity_str) if quantity_str else 0
    reason = request.form.get('reason')
    
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
    if product:
        stock_before = product.stock_quantity
        product.stock_quantity += quantity
        adj = StockAdjustment(
            product_id=product.id,
            quantity=quantity,
            reason=reason,
            stock_snapshot=stock_before,
            user_id=current_user.id
        )
        db.session.add(adj)
        db.session.commit()
        flash('Stock adjusted successfully!')
    
    return redirect(url_for('inventory.list_adjustments'))
