from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from models import Invoice, Product, InvoiceItem, Shift, ProductVariant
from extensions import db
import datetime

returns_bp = Blueprint('returns', __name__)

@returns_bp.route('/api/invoice/return/<int:invoice_id>', methods=['POST'])
@login_required
def return_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    
    if invoice.status == 'returned':
        return jsonify({'error': 'Invoice already returned'}), 400
    
    current_shift = Shift.query.filter_by(user_id=current_user.id, status='open').first()
    if not current_shift:
        return jsonify({'error': 'No open shift found. Please open a shift to process returns.'}), 400
    
    # Restock products
    for item in invoice.items:
        product = Product.query.get(item.product_id)
        if product:
            product.stock_quantity += item.quantity
            
        # Restock variant if exists
        if item.variant_id:
            variant = ProductVariant.query.get(item.variant_id)
            if variant:
                variant.stock_quantity += item.quantity
    
    invoice.status = 'returned'
    
    # If it was a cash payment, deduct from current shift's expected cash
    if invoice.payment_mode == 'Cash':
        # Since shift.closing_cash calculation in routes_pos.py filters for 'completed' status,
        # we don't necessarily need to subtract it here if the invoice belongs to the CURRENT shift.
        # But if it belongs to an OLD shift, marking it 'returned' won't affect the current shift's cash balance.
        # For simplicity, we'll assume returns are handled with current drawer cash.
        pass

    db.session.commit()
    
    # Notify dashboard of return
    from extensions import socketio
    payload = {
        'amount': invoice.total_amount,
        'gst': invoice.total_gst,
        'cashier_id': invoice.cashier_id
    }
    socketio.emit('new_return', payload, room='admins')
    socketio.emit('new_return', payload, room=f"user_{invoice.cashier_id}")
    
    return jsonify({'success': True, 'message': 'Invoice returned and stock updated'})

@returns_bp.route('/api/invoice/search')
@login_required
def search_invoice():
    num = request.args.get('num')
    if not num:
        return jsonify({'error': 'Invoice number required'}), 400
        
    query = Invoice.query.filter_by(invoice_number=num)
    if current_user.role != 'admin':
        query = query.filter_by(cashier_id=current_user.id)
    invoice = query.first()
    if invoice:
        return jsonify({
            'id': invoice.id,
            'number': invoice.invoice_number,
            'date': invoice.timestamp.strftime('%Y-%m-%d %H:%M'),
            'amount': invoice.total_amount,
            'status': invoice.status
        })
    return jsonify({'error': 'Invoice not found'}), 404

@returns_bp.route('/returns')
@login_required
def returns_page():
    current_shift = Shift.query.filter_by(user_id=current_user.id, status='open').first()
    if not current_shift:
        flash('You must open a shift before processing returns.', 'warning')
        return redirect(url_for('pos.shifts_page'))
    return render_template('returns.html')
