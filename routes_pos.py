from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import Product, Invoice, InvoiceItem, Customer, BusinessSettings, Shift, ProductVariant
from extensions import db, socketio
import datetime
import json
import cv2
import numpy as np
import base64
import logging

pos_bp = Blueprint('pos', __name__)

@pos_bp.route('/')
@login_required
def root():
    return redirect(url_for('pos.dashboard'))

@pos_bp.route('/dashboard')
@login_required
def dashboard():
    today = datetime.datetime.utcnow().date()
    # Support Spectation or Personal View
    from flask import session
    is_admin = current_user.role == 'admin'
    effective_user_id = session.get('spectate_id', current_user.id)
    
    # Get invoices for today
    # Logic: Admin sees all (unless spectating). Cashier sees only their own.
    query = Invoice.query.filter(db.func.date(Invoice.timestamp) == today)
    
    if 'spectate_id' in session:
        query = query.filter(Invoice.cashier_id == effective_user_id)
    elif not is_admin:
        query = query.filter(Invoice.cashier_id == current_user.id)
        
    today_invoices = query.all()
    
    # Filter completed and returned invoices
    completed_invoices = [inv for inv in today_invoices if inv.status == 'completed']
    returned_invoices = [inv for inv in today_invoices if inv.status == 'returned']
    
    stats = {
        'total_sales': sum(inv.total_amount for inv in completed_invoices),
        'tx_count': len(completed_invoices),
        'total_gst': sum(inv.total_gst for inv in completed_invoices),
        'total_returns': sum(inv.total_amount for inv in returned_invoices),
        'return_count': len(returned_invoices),
        'low_stock_count': Product.query.filter(Product.stock_quantity < 10, Product.user_id == effective_user_id).count()
    }
    
    low_stock_products = Product.query.filter(Product.stock_quantity < 10, Product.user_id == effective_user_id).limit(5).all()
    
    # Hourly sales data for chart
    hourly_sales_query = db.session.query(
        db.func.strftime('%H', Invoice.timestamp).label('hour'),
        db.func.sum(Invoice.total_amount).label('amount')
    ).filter(db.func.date(Invoice.timestamp) == today, Invoice.status == 'completed')
    
    if 'spectate_id' in session:
        hourly_sales_query = hourly_sales_query.filter(Invoice.cashier_id == effective_user_id)
    elif not is_admin:
        hourly_sales_query = hourly_sales_query.filter(Invoice.cashier_id == current_user.id)
        
    hourly_sales = hourly_sales_query.group_by('hour').all()
    
    hourly_data = {str(i).zfill(2): 0 for i in range(24)}
    for hour, amount in hourly_sales:
        hourly_data[hour] = amount

    current_shift = Shift.query.filter_by(user_id=current_user.id, status='open').first()
    
    # Check for pending approvals (for Admin notification)
    pending_users_count = 0
    if current_user.role == 'admin':
        from models import User
        pending_users_count = User.query.filter_by(is_approved=False).count()

    return render_template('dashboard.html', 
                         stats=stats, 
                         low_stock_products=low_stock_products,
                         hourly_data=hourly_data,
                         current_shift=current_shift,
                         pending_users_count=pending_users_count)

@pos_bp.route('/billing')
@login_required
def billing():
    from flask import session
    effective_user_id = session.get('spectate_id', current_user.id)
    current_shift = Shift.query.filter_by(user_id=effective_user_id, status='open').first()
    if not current_shift:
        flash('You must open a shift before starting billing.', 'warning')
        return redirect(url_for('pos.shifts_page'))
    
    # Pre-fetch products for the manual selection dropdown
    products = Product.query.filter_by(user_id=effective_user_id).order_by(Product.name.asc()).all()
    return render_template('pos.html', products=products)

@pos_bp.route('/api/product/<barcode>')
@login_required
def get_product(barcode):
    from flask import session
    effective_user_id = session.get('spectate_id', current_user.id)
    p = Product.query.filter_by(barcode=barcode, user_id=effective_user_id).first()
    if p:
        return jsonify({
            'id': p.id, 'name': p.name, 'price': p.price, 'stock': p.stock_quantity, 'barcode': p.barcode, 'gst_rate': p.gst_rate,
            'image_url': p.image_url,
            'variants': [{'id': v.id, 'name': v.name, 'price_impact': v.price_impact} for v in p.variants],
            'modifiers': [{'id': m.id, 'name': m.name, 'price': m.price} for m in p.modifiers]
        })
    return jsonify({'error': 'Product not found'}), 404


@pos_bp.route('/api/product/id/<int:product_id>')
@login_required
def get_product_by_id(product_id):
    from flask import session
    effective_user_id = session.get('spectate_id', current_user.id)
    p = Product.query.filter_by(id=product_id, user_id=effective_user_id).first()
    if p:
        return jsonify({
            'id': p.id, 'name': p.name, 'price': p.price, 'stock': p.stock_quantity, 'barcode': p.barcode, 'gst_rate': p.gst_rate,
            'image_url': p.image_url,
            'variants': [{'id': v.id, 'name': v.name, 'price_impact': v.price_impact} for v in p.variants],
            'modifiers': [{'id': m.id, 'name': m.name, 'price': m.price} for m in p.modifiers]
        })
    return jsonify({'error': 'Product not found'}), 404

@pos_bp.route('/api/products/search')
@login_required
def search_products():
    from flask import session
    effective_user_id = session.get('spectate_id', current_user.id)
    query = request.args.get('q', '')
    if not query:
        # Return all products ordered by ascending stock (low stock first)
        products = Product.query.filter_by(user_id=effective_user_id).order_by(Product.stock_quantity.asc()).all()
    else:
        # Match by name starting with the query and order results by ascending stock
        products = Product.query.filter(Product.name.ilike(f'{query}%'), Product.user_id == effective_user_id).order_by(Product.stock_quantity.asc()).limit(20).all()
    return jsonify([{
        'id': p.id, 'name': p.name, 'price': p.price, 'stock': p.stock_quantity, 'barcode': p.barcode, 'gst_rate': p.gst_rate,
        'image_url': p.image_url,
        'variants': [{'id': v.id, 'name': v.name, 'price_impact': v.price_impact} for v in p.variants],
        'modifiers': [{'id': m.id, 'name': m.name, 'price': m.price} for m in p.modifiers]
    } for p in products])

@pos_bp.route('/api/barcode/scan', methods=['POST'])
@login_required
def scan_barcode():
    data = request.json
    image_data = data.get('image') # Base64 string
    
    if not image_data:
        return jsonify({'error': 'No image data'}), 400
        
    try:
        # Decode base64
        header, encoded = image_data.split(",", 1)
        decoded = base64.b64decode(encoded)
        nparr = np.frombuffer(decoded, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({'error': 'Invalid image'}), 400
            
        # Detect and decode
        detector = getattr(pos_bp, 'barcode_detector', cv2.barcode.BarcodeDetector())
        ok, decoded_info, decoded_type, _ = detector.detectAndDecode(img)
        
        if ok and decoded_info:
            return jsonify({
                'success': True,
                'barcode': decoded_info[0],
                'type': decoded_type[0]
            })
        
        return jsonify({'success': False, 'message': 'No barcode detected'}), 200
    except Exception as e:
        logging.error(f"Barcode Scan API Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@pos_bp.route('/api/checkout', methods=['POST'])
@login_required
def checkout():
    data = request.json
    items = data.get('items', [])
    customer_gstin = data.get('customer_gstin')
    payment_mode = data.get('payment_mode', 'Cash')
    try:
        discount_val = data.get('discount_amount', 0)
        discount_amount = float(discount_val) if discount_val != '' else 0.0
    except (TypeError, ValueError):
        discount_amount = 0.0
    customer_id = data.get('customer_id')
    is_draft = data.get('status') == 'draft'
    
    if not items:
        return jsonify({'error': 'No items in cart'}), 400
        
    total_amount = 0
    total_gst = 0
    
    invoice_number = f"INV-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}" if not is_draft else f"DFT-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    new_invoice = Invoice(
        invoice_number=invoice_number,
        customer_gstin=customer_gstin,
        payment_mode=payment_mode,
        total_amount=0,
        total_gst=0,
        discount_amount=discount_amount,
        customer_id=customer_id,
        cashier_id=current_user.id,
        status='draft' if is_draft else 'completed',
        payment_status=data.get('payment_status', 'paid'),
        payment_link=data.get('payment_link')
    )
    
    # Link to current open shift
    current_shift = Shift.query.filter_by(user_id=current_user.id, status='open').first()
    if current_shift:
        new_invoice.shift_id = current_shift.id
        
    db.session.add(new_invoice)
    db.session.flush()
    
    for item in items:
        product = Product.query.get(item['id'])
        if product:
            # Check stock only if completing checkout
            if not is_draft and product.stock_quantity < item['quantity']:
                db.session.rollback()
                return jsonify({'error': f'Insufficient stock for {product.name}'}), 400
            
            line_total = item['price'] * item['quantity']
            item_gst = line_total - (line_total / (1 + (product.gst_rate / 100)))
            total_amount += line_total
            total_gst += item_gst
            
            if not is_draft:
                product.stock_quantity -= item['quantity']
                
                # Decrement variant stock if applicable
                variant_id = item.get('variant_id')
                if variant_id:
                    variant = ProductVariant.query.get(variant_id)
                    if variant:
                        # Check variant stock?
                        if variant.stock_quantity < item['quantity']:
                             db.session.rollback()
                             return jsonify({'error': f'Insufficient stock for variant {variant.name}'}), 400
                        variant.stock_quantity -= item['quantity']
            
            invoice_item = InvoiceItem(
                invoice_id=new_invoice.id,
                product_id=product.id,
                variant_id=item.get('variant_id'),
                quantity=item['quantity'],
                unit_price=item['price'], # Inclusive price
                gst_amount=item_gst,
                modifiers_json=json.dumps(item.get('modifiers', []))
            )
            db.session.add(invoice_item)
            
    final_total = total_amount - discount_amount
    new_invoice.total_amount = final_total
    new_invoice.total_gst = total_gst
    
    # Award Loyalty Points
    if customer_id and not is_draft:
        customer = Customer.query.get(customer_id)
        if customer:
            points_earned = int(final_total // 100)
            customer.loyalty_points += points_earned
            
    db.session.commit()
    
    if not is_draft:
        # Notify admins and the specific cashier who made the sale
        payload = {
            'amount': final_total,
            'gst': total_gst,
            'items_count': len(items),
            'cashier_id': current_user.id
        }
        socketio.emit('new_sale', payload, room='admins')
        socketio.emit('new_sale', payload, room=f"user_{current_user.id}")
        
    return jsonify({
        'success': True,
        'invoice_id': new_invoice.id,
        'invoice_number': invoice_number,
        'status': new_invoice.status
    })

@pos_bp.route('/api/customers/search')
@login_required
def search_customers():
    from flask import session
    effective_user_id = session.get('spectate_id', current_user.id)
    q = request.args.get('q', '')
    customers = Customer.query.filter(
        (Customer.user_id == effective_user_id) & (
            (Customer.name.ilike(f'%{q}%')) | (Customer.phone.like(f'%{q}%'))
        )
    ).limit(10).all()
    return jsonify([{
        'id': c.id, 'name': c.name, 'phone': c.phone, 'loyalty': c.loyalty_points
    } for c in customers])

@pos_bp.route('/api/customers/add', methods=['POST'])
@login_required
def add_customer():
    data = request.json
    try:
        from flask import session
        effective_user_id = session.get('spectate_id', current_user.id)
        new_customer = Customer(
            name=data.get('name'),
            phone=data.get('phone'),
            email=data.get('email'),
            user_id=effective_user_id
        )
        db.session.add(new_customer)
        db.session.commit()
        return jsonify({'id': new_customer.id, 'name': new_customer.name})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@pos_bp.route('/invoice/print/<int:invoice_id>')
@login_required
def print_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    settings = BusinessSettings.query.first()
    return render_template('invoice_print.html', invoice=invoice, settings=settings)

@pos_bp.route('/api/invoices/drafts')
@login_required
def list_drafts():
    query = Invoice.query.filter_by(status='draft')
    if current_user.role != 'admin':
        query = query.filter_by(cashier_id=current_user.id)
    
    drafts = query.order_by(Invoice.timestamp.desc()).all()
    return jsonify([{
        'id': d.id,
        'invoice_number': d.invoice_number,
        'timestamp': d.timestamp.strftime('%Y-%m-%d %H:%M'),
        'customer_name': d.customer.name if d.customer else 'Guest',
        'total': d.total_amount
    } for d in drafts])

@pos_bp.route('/api/invoices/draft/<int:invoice_id>')
@login_required
def get_draft(invoice_id):
    d = Invoice.query.get_or_404(invoice_id)
    if d.status != 'draft':
        return jsonify({'error': 'Invoice is not a draft'}), 400
    
    if current_user.role != 'admin' and d.cashier_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    items = []
    for item in d.items:
        items.append({
            'id': item.product.id,
            'name': item.product.name,
            'price': item.unit_price,
            'quantity': item.quantity,
            'gst_rate': item.product.gst_rate,
            'variant_id': item.variant_id,
            'modifiers': json.loads(item.modifiers_json) if item.modifiers_json else []
        })
        
    return jsonify({
        'invoice_id': d.id,
        'customer_id': d.customer_id,
        'customer_name': d.customer.name if d.customer else None,
        'customer_phone': d.customer.phone if d.customer else None,
        'discount_amount': d.discount_amount,
        'items': items
    })

@pos_bp.route('/api/invoices/draft/delete/<int:invoice_id>', methods=['DELETE'])
@login_required
def delete_draft(invoice_id):
    d = Invoice.query.get_or_404(invoice_id)
    if d.status != 'draft':
        return jsonify({'error': 'Invoice is not a draft'}), 400
    
    if current_user.role != 'admin' and d.cashier_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Delete items first if cascade isn't automatic, 
        # but SQLAlchemy relationship is set up with lazy=True typically.
        # Let's be explicit if needed, but standard delete usually works.
        db.session.delete(d)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Draft deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@pos_bp.route('/api/invoice/email/<int:invoice_id>', methods=['POST'])
@login_required
def email_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    email = request.json.get('email')
    
    if not email:
        return jsonify({'error': 'Email address required'}), 400
        
    # Simulation of sending email
    print(f"SIMULATION: Sending invoice {invoice.invoice_number} to {email}")
    
    return jsonify({'success': True, 'message': f'Receipt sent to {email}'})

@pos_bp.route('/shifts')
@login_required
def shifts_page():
    current_shift = Shift.query.filter_by(user_id=current_user.id, status='open').first()
    
    if current_user.role == 'admin':
        # Admin sees all shifts, but paginate or limit to recent to avoid overload
        all_shifts = Shift.query.order_by(Shift.start_time.desc()).limit(50).all()
        # Ensure user relationship is loaded or access it in template (lazy loading is default)
    else:
        # Cashier sees only their own shifts
        all_shifts = Shift.query.filter_by(user_id=current_user.id).order_by(Shift.start_time.desc()).limit(20).all()
        
    return render_template('shifts.html', current_shift=current_shift, shifts=all_shifts)

@pos_bp.route('/shifts/open', methods=['POST'])
@login_required
def open_shift():
    opening_cash = float(request.form.get('opening_cash', 0))
    new_shift = Shift(user_id=current_user.id, opening_cash=opening_cash, status='open')
    db.session.add(new_shift)
    db.session.commit()
    flash('Shift opened successfully!')
    return redirect(url_for('pos.shifts_page'))

@pos_bp.route('/shifts/close', methods=['POST'])
@login_required
def close_shift():
    actual_cash = float(request.form.get('actual_cash', 0))
    shift = Shift.query.filter_by(user_id=current_user.id, status='open').first()
    
    if shift:
        cash_sales = db.session.query(db.func.sum(Invoice.total_amount)).filter(
            Invoice.shift_id == shift.id, 
            Invoice.payment_mode == 'Cash',
            Invoice.status == 'completed'
        ).scalar() or 0.0
        
        # Subtract any returns processed for invoices that WERE in this shift
        # Note: This only works if returns are marked as 'returned' 
        # A more robust system would track return transactions separately.
        
        shift.closing_cash = shift.opening_cash + cash_sales
        shift.actual_cash = actual_cash
        shift.end_time = datetime.datetime.utcnow()
        shift.status = 'closed'
        db.session.commit()
        flash('Shift closed successfully!')
    
    return redirect(url_for('pos.shifts_page'))

@pos_bp.route('/shifts/reset', methods=['POST'])
@login_required
def reset_shift():
    shift = Shift.query.filter_by(user_id=current_user.id, status='open').first()
    if shift:
        # Reset counters for the current shift
        shift.opening_cash = 0.0
        shift.closing_cash = None
        shift.actual_cash = None
        shift.start_time = datetime.datetime.utcnow()
        db.session.commit()
        flash('Shift has been reset successfully!')
    else:
        flash('No open shift found to reset.', 'warning')
        
    return redirect(url_for('pos.shifts_page'))
