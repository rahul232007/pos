from flask import Blueprint, render_template, Response, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import Invoice, InvoiceItem, Product, User
from extensions import db
import io
import csv

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports/export/daily')
@login_required
def export_daily_sales():
    query = db.session.query(
        db.func.date(Invoice.timestamp).label('date'),
        db.func.sum(Invoice.total_amount).label('total_sales'),
        db.func.sum(Invoice.total_gst).label('total_gst'),
        db.func.count(Invoice.id).label('tx_count')
    )
    
    if current_user.role != 'admin':
        query = query.filter(Invoice.cashier_id == current_user.id)
        
    daily_stats = query.group_by(db.func.date(Invoice.timestamp)).order_by(db.desc('date')).all()
    
    def generate():
        data = io.StringIO()
        writer = csv.writer(data)
        writer.writerow(['Date', 'Transactions', 'Total Sales', 'Total GST', 'Net Revenue'])
        yield data.getvalue()
        data.truncate(0)
        data.seek(0)
        
        for s in daily_stats:
            writer.writerow([s.date, s.tx_count, s.total_sales, s.total_gst, s.total_sales - s.total_gst])
            yield data.getvalue()
            data.truncate(0)
            data.seek(0)

    response = Response(generate(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename="daily_sales.csv")
    return response

@reports_bp.route('/reports/export/transactions')
@login_required
def export_transactions():
    query = Invoice.query
    if current_user.role != 'admin':
        query = query.filter_by(cashier_id=current_user.id)
    invoices = query.order_by(Invoice.timestamp.desc()).all()
    
    def generate():
        data = io.StringIO()
        writer = csv.writer(data)
        writer.writerow(['Invoice No', 'Date', 'Customer Name', 'Customer GSTIN', 'Payment Mode', 'Payment Status', 'Payment Link', 'Total Amount', 'Total GST'])
        yield data.getvalue()
        data.truncate(0)
        data.seek(0)
        
        for inv in invoices:
            cust_name = inv.customer.name if inv.customer else 'Walk-in'
            writer.writerow([inv.invoice_number, inv.timestamp, cust_name, inv.customer_gstin, inv.payment_mode, inv.payment_status, inv.payment_link, inv.total_amount, inv.total_gst])
            yield data.getvalue()
            data.truncate(0)
            data.seek(0)

    response = Response(generate(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename="transactions.csv")
    return response

@reports_bp.route('/reports')
@login_required
def index():
    query = Invoice.query
    if current_user.role != 'admin':
        query = query.filter_by(cashier_id=current_user.id)
    invoices = query.order_by(Invoice.timestamp.desc()).all()
    total_sales = sum(inv.total_amount for inv in invoices)
    total_gst = sum(inv.total_gst for inv in invoices)
    return render_template('reports.html', invoices=invoices, total_sales=total_sales, total_gst=total_gst)

@reports_bp.route('/reports/analytics')
@login_required
def analytics():
    is_admin = current_user.role == 'admin'
    
    # Top Selling Products
    products_query = db.session.query(
        Product.name,
        db.func.sum(InvoiceItem.quantity).label('units_sold'),
        db.func.sum(InvoiceItem.quantity * InvoiceItem.unit_price).label('revenue')
    ).join(InvoiceItem, Product.id == InvoiceItem.product_id).join(Invoice, Invoice.id == InvoiceItem.invoice_id)
    
    if not is_admin:
        products_query = products_query.filter(Invoice.cashier_id == current_user.id)
        
    top_products = products_query.group_by(Product.name).order_by(db.desc('units_sold')).limit(5).all()

    return render_template('reports_analytics.html', 
                         top_products=top_products)

@reports_bp.route('/reports/invoice/delete/<int:invoice_id>')
@login_required
def delete_invoice(invoice_id):
    if current_user.role != 'admin':
        flash('Access denied.')
        return redirect(url_for('reports.index'))
        
    inv = Invoice.query.get_or_404(invoice_id)
    try:
        # Revert Stock for items
        for item in inv.items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock_quantity += item.quantity
        
        db.session.delete(inv) # Cascading should handle items
        db.session.commit()
        flash(f'Invoice {inv.invoice_number} deleted and stock reverted.')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting invoice: {str(e)}')
        
    return redirect(url_for('reports.index'))

@reports_bp.route('/reports/invoice/void/<int:invoice_id>')
@login_required
def void_invoice(invoice_id):
    if current_user.role != 'admin':
        flash('Access denied.')
        return redirect(url_for('reports.index'))
        
    inv = Invoice.query.get_or_404(invoice_id)
    inv.status = 'voided'
    db.session.commit()
    flash(f'Invoice {inv.invoice_number} has been voided.')
    return redirect(url_for('reports.index'))

@reports_bp.route('/api/invoice/search')
@login_required
def search_invoice():
    num = request.args.get('num', '')
    query = Invoice.query.filter_by(invoice_number=num)
    if current_user.role != 'admin':
        query = query.filter_by(cashier_id=current_user.id)
    inv = query.first()
    if inv:
        return jsonify({
            'id': inv.id,
            'number': inv.invoice_number,
            'date': inv.timestamp.strftime('%d-%m-%Y %H:%M'),
            'amount': inv.total_amount,
            'status': inv.status,
            'payment_status': inv.payment_status,
            'payment_link': inv.payment_link
        })
    return jsonify({'error': 'Not found'}), 404
