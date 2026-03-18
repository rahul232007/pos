from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import BusinessSettings, User
from extensions import db
from functools import wraps
import os
import shutil
from datetime import datetime
from flask import send_from_directory, current_app

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Access denied: Admin privileges required.')
            return redirect(url_for('pos.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    settings = BusinessSettings.query.filter_by(user_id=current_user.id).first()
    if not settings:
        settings = BusinessSettings(user_id=current_user.id)
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        settings.company_name = request.form.get('company_name')
        settings.gstin = request.form.get('gstin')
        settings.address = request.form.get('address')
        settings.phone = request.form.get('phone')
        settings.email = request.form.get('email')
        db.session.commit()
        flash('Business settings updated successfully!')
        return redirect(url_for('admin.settings'))

    # List backups
    backups = []
    backup_dir = os.path.join(current_app.root_path, 'backups')
    if os.path.exists(backup_dir):
        backups = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
        backups.sort(reverse=True) # Newest first

    return render_template('admin_settings.html', settings=settings, backups=backups)

@admin_bp.route('/admin/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('user_list.html', users=users)

@admin_bp.route('/admin/users/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.full_name = request.form.get('full_name')
        user.email = request.form.get('email')
        user.mobile = request.form.get('mobile')
        user.country_code = request.form.get('country_code', '+91')
        user.role = request.form.get('role', 'cashier')
        
        try:
            db.session.commit()
            flash(f'Details updated for {user.username}!')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}')
            
        return redirect(url_for('admin.user_detail', user_id=user.id))
        
    return render_template('admin_user_detail.html', user=user)

@admin_bp.route('/admin/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    username = request.form.get('username')
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    mobile = request.form.get('mobile')
    country_code = request.form.get('country_code', '+91')
    password = request.form.get('password')
    role = request.form.get('role', 'cashier')

    if User.query.filter_by(username=username).first():
        flash('Username already exists!')
    else:
        new_user = User(
            username=username, 
            full_name=full_name, 
            email=email,
            mobile=mobile,
            country_code=country_code,
            role=role, 
            is_approved=True,
            is_verified=True # Admin created users are pre-verified
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully!')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/admin/users/approve/<int:user_id>')
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    flash(f'User {user.username} approved!')
    return redirect(url_for('admin.users'))

@admin_bp.route('/admin/users/reset_password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')
    if new_password:
        user.set_password(new_password)
        db.session.commit()
        flash(f'Password reset for {user.username}!')
    return redirect(url_for('admin.users'))

@admin_bp.route('/admin/users/delete/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete yourself!')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully!')
    return redirect(url_for('admin.users'))

# --- SPECTATE API ---

@admin_bp.route('/api/admin/users/list')
@login_required
@admin_required
def api_list_users():
    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'full_name': u.full_name,
        'role': u.role,
        'is_approved': u.is_approved,
        'spectate_url': url_for('admin.start_spectate', user_id=u.id)
    } for u in users])

@admin_bp.route('/admin/spectate/<int:user_id>')
@login_required
@admin_required
def start_spectate(user_id):
    if user_id == current_user.id:
        flash('You are already yourself.')
        return redirect(url_for('pos.dashboard'))
    
    user = User.query.get_or_404(user_id)
    from flask import session
    session['spectate_id'] = user.id
    flash(f'Now spectating as {user.username}. Some views will reflect their data.')
    return redirect(url_for('pos.dashboard'))

@admin_bp.route('/admin/stop-spectate')
@login_required
def stop_spectate():
    from flask import session
    if 'spectate_id' in session:
        session.pop('spectate_id')
        flash('Spectation ended. You are back to Admin view.')
    return redirect(url_for('admin.users'))

# --- DATA MANAGEMENT (BACKUP / RESET / RESTORE) ---

@admin_bp.route('/admin/data/backup', methods=['POST'])
@login_required
@admin_required
def create_backup():
    try:
        backup_dir = os.path.join(current_app.root_path, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        db_path = os.path.join(current_app.root_path, 'instance', 'pos.db')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"pos_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy the database file
        shutil.copy2(db_path, backup_path)
        
        flash(f'Backup created successfully: {backup_filename}')
    except Exception as e:
        flash(f'Error creating backup: {str(e)}', 'danger')
        
    return redirect(url_for('admin.settings'))

@admin_bp.route('/admin/data/reset', methods=['POST'])
@login_required
@admin_required
def reset_data():
    try:
        # 1. Create auto-backup before reset
        backup_dir = os.path.join(current_app.root_path, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        db_path = os.path.join(current_app.root_path, 'instance', 'pos.db')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_AUTO_BEFORE_RESET')
        backup_path = os.path.join(backup_dir, f"pos_auto_backup_{timestamp}.db")
        shutil.copy2(db_path, backup_path)
        
        # 2. Reset Transactional Tables
        from models import Product, Invoice, InvoiceItem, Shift, StockAdjustment, ProductVariant, ProductModifier
        
        db.session.query(InvoiceItem).delete()
        db.session.query(Invoice).delete()
        db.session.query(StockAdjustment).delete()
        db.session.query(Shift).delete()
        db.session.query(ProductVariant).delete()
        db.session.query(ProductModifier).delete()
        # Drop link table if exists (manual query if needed, but models should handle cascading if set up)
        db.session.execute(db.text("DELETE FROM product_modifier_links"))
        
        db.session.query(Product).delete()
        
        db.session.commit()
        flash('All transactional and product data has been reset. A backup was created automatically.')
    except Exception as e:
        db.session.rollback()
        flash(f'Error during reset: {str(e)}', 'danger')
        
    return redirect(url_for('admin.settings'))

@admin_bp.route('/admin/data/restore/<filename>', methods=['POST'])
@login_required
@admin_required
def restore_backup(filename):
    try:
        backup_dir = os.path.join(current_app.root_path, 'backups')
        backup_path = os.path.join(backup_dir, filename)
        db_path = os.path.join(current_app.root_path, 'instance', 'pos.db')
        
        if not os.path.exists(backup_path):
            flash('Backup file not found.', 'danger')
            return redirect(url_for('admin.settings'))
            
        # To restore, we need to close current connections if possible.
        # For SQLite, copying over the file while the app is running is risky but often works 
        # for low-traffic apps. A safer way is via SQL dump/load, but file copy is faster.
        
        # Create a "safety" backup of the CURRENT db before overwriting
        shutil.copy2(db_path, db_path + ".tmp")
        
        try:
            # Overwrite active DB with backup
            shutil.copy2(backup_path, db_path)
            flash(f'Database restored successfully from {filename}')
        except Exception as copy_err:
            shutil.move(db_path + ".tmp", db_path) # Restore original if copy failed
            raise copy_err
        finally:
            if os.path.exists(db_path + ".tmp"):
                os.remove(db_path + ".tmp")
                
    except Exception as e:
        flash(f'Error during restore: {str(e)}', 'danger')
        
    return redirect(url_for('admin.settings'))

