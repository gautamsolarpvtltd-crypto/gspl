from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import random
import string
from datetime import datetime, timedelta
from functools import wraps
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, template_folder='.', static_folder='.')
app.secret_key = 'super-secret-key-change-in-production'

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'database', 'certportal.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== EMAIL CONFIGURATION ====================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
ADMIN_EMAIL = "gautamsolarpvtltd@gmail.com"
ADMIN_PASSWORD = "your_app_password_here"  # Update this with Gmail App Password

def send_email(recipient, subject, body, is_html=False):
    """Send email notification"""
    try:
        msg = MIMEMultipart()
        msg['From'] = ADMIN_EMAIL
        msg['To'] = recipient
        msg['Subject'] = subject
        
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {str(e)}")
        return False

# ==================== MODELS ====================
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    mobile = db.Column(db.String(20))
    password = db.Column(db.String(255), nullable=False)
    approved = db.Column(db.Boolean, default=False)

class PasswordReset(db.Model):
    __tablename__ = 'password_reset'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    otp_type = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    used = db.Column(db.Boolean, default=False)

class AccessRequest(db.Model):
    __tablename__ = 'access_request'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    request_type = db.Column(db.String(50))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notified = db.Column(db.Boolean, default=False)

class ProductCategory(db.Model):
    __tablename__ = 'product_category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)
    products = db.relationship('Product', backref='category', lazy=True, cascade='all, delete-orphan')

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('product_category.id'), nullable=False)
    wattage = db.Column(db.String(50), nullable=False)
    order = db.Column(db.Integer, default=0)
    availability = db.Column(db.String(20), default='available')
    documents = db.relationship('Document', backref='product', lazy=True, cascade='all, delete-orphan')

class Document(db.Model):
    __tablename__ = 'document'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    doc_type = db.Column(db.String(100), nullable=False)
    doc_name = db.Column(db.String(200))
    download_link = db.Column(db.String(500), nullable=False)
    order = db.Column(db.Integer, default=0)

class CompanyDocument(db.Model):
    __tablename__ = 'company_document'
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100), nullable=False)
    doc_type = db.Column(db.String(100), nullable=False)
    doc_name = db.Column(db.String(200))
    download_link = db.Column(db.String(500), nullable=False)

class HomeNotification(db.Model):
    __tablename__ = 'home_notification'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    notification_type = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    order = db.Column(db.Integer, default=0)

# ==================== ROUTES ====================
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('assets', filename)

@app.route("/")
def index():
    notifications = HomeNotification.query.filter_by(is_active=True).order_by(HomeNotification.order).all()
    return render_template("index.html", notifications=notifications)

@app.route("/about")
def about():
    """About Us page"""
    return render_template("about.html")

@app.route("/contact")
def contact():
    """Contact page with company information"""
    return render_template("contact.html")

@app.route("/portal")
def portal():
    is_logged_in = "user_id" in session
    user_name = session.get("user_name", "")
    return render_template("portal_new.html", is_logged_in=is_logged_in, user_name=user_name)

@app.route("/download/<int:doc_id>")
def download_document(doc_id):
    if "user_id" not in session:
        return redirect(url_for("login", next=request.url))
    doc = Document.query.get_or_404(doc_id)
    return redirect(doc.download_link)

@app.route("/download/company/<int:doc_id>")
def download_company_doc(doc_id):
    if "user_id" not in session:
        return redirect(url_for("login", next=request.url))
    doc = CompanyDocument.query.get_or_404(doc_id)
    return redirect(doc.download_link)

@app.route("/api/portal-data")
def api_portal_data():
    categories = ProductCategory.query.order_by(ProductCategory.order).all()
    company_docs = CompanyDocument.query.all()
    is_logged_in = "user_id" in session
    
    company_data = {}
    for doc in company_docs:
        if doc.location not in company_data:
            company_data[doc.location] = []
        company_data[doc.location].append({
            'id': doc.id,
            'type': doc.doc_type,
            'name': doc.doc_name or doc.doc_type,
            'link': f'/download/company/{doc.id}' if is_logged_in else '/login',
            'requires_login': not is_logged_in
        })
    
    products_data = []
    for cat in categories:
        products = Product.query.filter_by(category_id=cat.id).order_by(Product.order).all()
        products_list = []
        for prod in products:
            docs = Document.query.filter_by(product_id=prod.id).order_by(Document.order).all()
            products_list.append({
                'id': prod.id,
                'wattage': prod.wattage,
                'availability': prod.availability,
                'documents': [{
                    'id': d.id,
                    'type': d.doc_type,
                    'name': d.doc_name or d.doc_type,
                    'link': f'/download/{d.id}' if is_logged_in else '/login',
                    'requires_login': not is_logged_in
                } for d in docs]
            })
        
        products_data.append({
            'id': cat.id,
            'name': cat.name,
            'description': cat.description,
            'products': products_list
        })
    
    return jsonify({
        'companyDocs': company_data,
        'categories': products_data,
        'isLoggedIn': is_logged_in
    })

# ==================== PASSWORD RESET ROUTES ====================
def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return "Email not found in our system!"
        
        otp = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        PasswordReset.query.filter_by(user_id=user.id, used=False).delete()
        
        pwd_reset = PasswordReset(user_id=user.id, otp=otp, otp_type='email', expires_at=expires_at)
        db.session.add(pwd_reset)
        db.session.commit()
        
        send_email(user.email, "Password Reset OTP - Gautam Solar", 
                  f"Your OTP for password reset is: {otp}\n\nThis OTP is valid for 10 minutes.")
        
        access_req = AccessRequest(user_id=user.id, request_type='password_reset', 
                                  details=f"Password reset requested by {user.email}")
        db.session.add(access_req)
        db.session.commit()
        
        admin_subject = "🔐 Password Reset Request - Gautam Solar Portal"
        admin_body = f"""
        <h2>Password Reset Request</h2>
        <p><strong>User Name:</strong> {user.name}</p>
        <p><strong>Email:</strong> {user.email}</p>
        <p><strong>Mobile:</strong> {user.mobile}</p>
        <p><strong>Company:</strong> {user.company}</p>
        <p><strong>Timestamp:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        send_email(ADMIN_EMAIL, admin_subject, admin_body, is_html=True)
        
        return redirect(url_for("verify_otp", user_email=email, reset_type='email'))
    
    return render_template("forgot_password.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    user_email = request.args.get("user_email")
    reset_type = request.args.get("reset_type", "email")
    
    if request.method == "POST":
        otp = request.form.get("otp")
        user = User.query.filter_by(email=user_email).first()
        
        if not user:
            return "User not found!"
        
        pwd_reset = PasswordReset.query.filter_by(user_id=user.id, used=False).order_by(PasswordReset.created_at.desc()).first()
        
        if not pwd_reset:
            return "No active OTP request found!"
        
        if pwd_reset.expires_at < datetime.utcnow():
            return "OTP has expired! Request a new one."
        
        if pwd_reset.otp != otp:
            return "Invalid OTP!"
        
        pwd_reset.used = True
        db.session.commit()
        
        return redirect(url_for("reset_password", user_email=user_email, token=pwd_reset.id))
    
    return render_template("verify_otp.html", user_email=user_email, reset_type=reset_type)

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    user_email = request.args.get("user_email")
    token = request.args.get("token")
    
    if request.method == "POST":
        new_password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        if new_password != confirm_password:
            return "Passwords do not match!"
        
        if len(new_password) < 6:
            return "Password must be at least 6 characters!"
        
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return "User not found!"
        
        user.password = generate_password_hash(new_password)
        db.session.commit()
        
        send_email(user.email, "Password Reset Successful - Gautam Solar",
                  "Your password has been successfully reset. You can now login with your new password.")
        
        return redirect(url_for("login"))
    
    return render_template("reset_password.html", user_email=user_email)

# ==================== USER REGISTRATION ====================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()
        company = request.form.get("company", "").strip()
        mobile = request.form.get("mobile", "").strip()
        
        print(f"\n📝 Registration attempt:")
        print(f"   Email: {email}")
        print(f"   Name: {name}")
        print(f"   Company: {company}")
        
        if not email or not password or not name:
            return """
            <style>body{font-family:Arial;padding:40px;background:#f7fafc}</style>
            <div style="max-width:600px;margin:0 auto;background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1)">
                <h2 style="color:#f56565">❌ Registration Failed</h2>
                <p>Email, name, and password are required!</p>
                <br>
                <a href="/register" style="color:#667eea">← Try again</a>
            </div>
            """
        
        if len(password) < 6:
            return """
            <style>body{font-family:Arial;padding:40px;background:#f7fafc}</style>
            <div style="max-width:600px;margin:0 auto;background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1)">
                <h2 style="color:#f56565">❌ Password Too Short</h2>
                <p>Password must be at least 6 characters!</p>
                <br>
                <a href="/register" style="color:#667eea">← Try again</a>
            </div>
            """
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return """
            <style>body{font-family:Arial;padding:40px;background:#f7fafc}</style>
            <div style="max-width:600px;margin:0 auto;background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1)">
                <h2 style="color:#f56565">❌ Email Already Registered</h2>
                <p>This email is already registered in our system.</p>
                <p>Please <a href="/login" style="color:#667eea">login here</a> or use a different email.</p>
                <br>
                <a href="/register" style="color:#667eea">← Try again</a>
            </div>
            """
        
        try:
            user = User(
                name=name,
                company=company or "Not specified",
                email=email,
                mobile=mobile or "Not provided",
                password=generate_password_hash(password),
                approved=False
            )
            
            db.session.add(user)
            db.session.commit()
            
            print(f"✅ User created successfully:")
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Approved: {user.approved}")
            
            try:
                access_req = AccessRequest(
                    user_id=user.id,
                    request_type='new_registration',
                    details=f"New registration: {name} from {company or 'Not specified'}",
                    notified=False
                )
                db.session.add(access_req)
                db.session.commit()
                print(f"   ✓ Access request created")
            except Exception as e:
                print(f"   ⚠️ Access request failed: {e}")
            
            try:
                admin_subject = "📋 New User Registration - Gautam Solar Portal"
                admin_body = f"""
                <div style="font-family:Arial;padding:20px;background:#f7fafc">
                    <div style="max-width:600px;margin:0 auto;background:white;padding:30px;border-radius:10px">
                        <h2 style="color:#667eea">📋 New User Registration</h2>
                        <table style="width:100%;margin:20px 0">
                            <tr><td><strong>Name:</strong></td><td>{name}</td></tr>
                            <tr><td><strong>Email:</strong></td><td>{email}</td></tr>
                            <tr><td><strong>Mobile:</strong></td><td>{mobile or 'Not provided'}</td></tr>
                            <tr><td><strong>Company:</strong></td><td>{company or 'Not specified'}</td></tr>
                            <tr><td><strong>Time:</strong></td><td>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</td></tr>
                            <tr><td><strong>Status:</strong></td><td style="color:#ed8936">⏳ Pending Approval</td></tr>
                        </table>
                        <a href="http://127.0.0.1:5000/admin/users" 
                           style="display:inline-block;padding:12px 24px;background:#48bb78;color:white;text-decoration:none;border-radius:6px">
                            View & Approve User
                        </a>
                    </div>
                </div>
                """
                send_email(ADMIN_EMAIL, admin_subject, admin_body, is_html=True)
                print(f"   ✓ Admin notification email sent")
            except Exception as e:
                print(f"   ⚠️ Email notification failed: {e}")
            
            return f"""
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    padding: 40px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .container {{
                    max-width: 600px;
                    background: white;
                    padding: 40px;
                    border-radius: 15px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                }}
                h2 {{ color: #48bb78; margin-bottom: 20px; }}
                .info-box {{
                    background: #f0fff4;
                    border-left: 4px solid #48bb78;
                    padding: 20px;
                    margin: 20px 0;
                    text-align: left;
                }}
                .btn {{
                    display: inline-block;
                    margin: 10px 5px;
                    padding: 12px 24px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: 600;
                    transition: all 0.3s;
                }}
                .btn:hover {{ background: #5568d3; transform: translateY(-2px); }}
            </style>
            <div class="container">
                <h2>✅ Registration Successful!</h2>
                <p style="font-size:18px;margin:20px 0">Your account has been created.</p>
                
                <div class="info-box">
                    <strong>📧 Email:</strong> {email}<br>
                    <strong>👤 Name:</strong> {name}<br>
                    <strong>🏢 Company:</strong> {company or 'Not specified'}<br>
                    <strong>📱 Mobile:</strong> {mobile or 'Not provided'}
                </div>
                
                <div style="background:#fff3cd;border-left:4px solid #ffc107;padding:20px;margin:20px 0;text-align:left">
                    <strong>⏳ Approval Required</strong><br>
                    Your account is pending admin approval. This usually takes 24-48 hours.<br>
                    You will receive an email once approved.
                </div>
                
                <a href="/login" class="btn">Go to Login</a>
                <a href="/" class="btn" style="background:#718096">Back to Home</a>
            </div>
            """
        
        except Exception as e:
            db.session.rollback()
            print(f"❌ Registration error: {e}")
            import traceback
            traceback.print_exc()
            return f"""
            <style>body{{font-family:Arial;padding:40px;background:#f7fafc}}</style>
            <div style="max-width:600px;margin:0 auto;background:white;padding:30px;border-radius:10px">
                <h2 style="color:#f56565">❌ Registration Failed</h2>
                <p>Error: {str(e)}</p>
                <br>
                <a href="/register" style="color:#667eea">← Try again</a>
            </div>
            """
    
    return render_template("register.html")

# ==================== USER LOGIN ====================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        print(f"\n🔐 Login attempt: {email}")
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"   ❌ User not found: {email}")
            return """
            <style>body{font-family:Arial;padding:40px;background:#f7fafc}</style>
            <div style="max-width:600px;margin:0 auto;background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1)">
                <h2 style="color:#f56565">❌ Invalid Credentials</h2>
                <p><strong>Email not found in our system.</strong></p>
                <p>Please check your email or <a href="/register" style="color:#667eea">register here</a></p>
                <br>
                <a href="/login" style="color:#667eea">← Try again</a>
            </div>
            """
        
        print(f"   User found: ID={user.id}, Approved={user.approved}")
        
        if not check_password_hash(user.password, password):
            print(f"   ❌ Wrong password for: {email}")
            return """
            <style>body{font-family:Arial;padding:40px;background:#f7fafc}</style>
            <div style="max-width:600px;margin:0 auto;background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1)">
                <h2 style="color:#f56565">❌ Invalid Credentials</h2>
                <p><strong>Password is incorrect.</strong></p>
                <p>Please try again or <a href="/forgot-password" style="color:#667eea">reset your password</a></p>
                <br>
                <a href="/login" style="color:#667eea">← Try again</a>
            </div>
            """
        
        if not user.approved:
            print(f"   ⏳ Account pending approval: {email}")
            return """
            <style>
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    padding: 40px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
            </style>
            <div style="max-width:600px;background:white;padding:40px;border-radius:15px;box-shadow:0 20px 60px rgba(0,0,0,0.3);text-align:center">
                <h2 style="color:#ed8936">⏳ Account Pending Approval</h2>
                <p style="font-size:16px;margin:20px 0">Your account is awaiting admin approval.</p>
                <div style="background:#fff3cd;border-left:4px solid #ffc107;padding:20px;margin:20px 0;text-align:left">
                    <strong>What happens next?</strong><br>
                    • Admin will review your registration<br>
                    • You'll receive an email once approved<br>
                    • This usually takes 24-48 hours
                </div>
                <br>
                <a href="/login" style="display:inline-block;padding:12px 24px;background:#667eea;color:white;text-decoration:none;border-radius:8px">← Back to Login</a>
                <a href="/" style="display:inline-block;margin-left:10px;padding:12px 24px;background:#718096;color:white;text-decoration:none;border-radius:8px">Back to Home</a>
            </div>
            """
        
        print(f"   ✅ Login successful: {email}")
        session["user_id"] = user.id
        session["user_name"] = user.name
        
        try:
            access_req = AccessRequest(
                user_id=user.id,
                request_type='portal_access',
                details=f"Portal login from {request.remote_addr}"
            )
            db.session.add(access_req)
            db.session.commit()
        except Exception as e:
            print(f"   ⚠️ Could not log access: {e}")
        
        next_url = request.args.get('next')
        if next_url:
            print(f"   → Redirecting to: {next_url}")
            return redirect(next_url)
        
        print(f"   → Redirecting to portal")
        return redirect(url_for("portal"))
    
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("user_dashboard.html", user_name=session.get("user_name"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("portal"))

# ==================== ADMIN ROUTES ====================
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("email") == "gautamsolarpvtltd@gmail.com" and \
           request.form.get("password") == "Skpanchaladmin123":
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        return "Invalid admin credentials!"
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    
    users_count = User.query.count()
    approved_count = User.query.filter_by(approved=True).count()
    categories_count = ProductCategory.query.count()
    products_count = Product.query.count()
    pending_requests = AccessRequest.query.filter_by(notified=False).count()
    
    return render_template("admin_dashboard.html", 
                         users_count=users_count,
                         approved_count=approved_count,
                         categories_count=categories_count,
                         products_count=products_count,
                         pending_requests=pending_requests)

@app.route("/admin/users")
def admin_users():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    users = User.query.all()
    return render_template("admin_users.html", users=users)

@app.route("/admin/approve/<int:user_id>")
def approve_user(user_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    
    try:
        user = User.query.get_or_404(user_id)
        user.approved = True
        db.session.commit()
        
        print(f"✅ User approved: {user.email}")
        
        try:
            AccessRequest.query.filter_by(user_id=user.id, request_type='new_registration', notified=False).update({'notified': True})
            db.session.commit()
        except:
            pass
        
        try:
            send_email(
                user.email,
                "✅ Account Approved - Gautam Solar Portal",
                f"""
                <div style="font-family:Arial;padding:20px;background:#f7fafc">
                    <div style="max-width:600px;margin:0 auto;background:white;padding:30px;border-radius:10px">
                        <h2 style="color:#48bb78">✅ Your Account Has Been Approved!</h2>
                        <p>Dear {user.name},</p>
                        <p>Your account at Gautam Solar Portal has been approved and activated.</p>
                        
                        <div style="background:#f0fff4;border-left:4px solid #48bb78;padding:20px;margin:20px 0">
                            <strong>Login Details:</strong><br>
                            <strong>Email:</strong> {user.email}<br>
                            <strong>Portal:</strong> <a href="http://127.0.0.1:5000/login">http://127.0.0.1:5000/login</a>
                        </div>
                        
                        <a href="http://127.0.0.1:5000/login" 
                           style="display:inline-block;padding:12px 24px;background:#667eea;color:white;text-decoration:none;border-radius:8px;margin:10px 0">
                            Login Now
                        </a>
                        
                        <p style="margin-top:20px;color:#666;font-size:14px">
                            Thank you,<br>
                            <strong>Gautam Solar Team</strong>
                        </p>
                    </div>
                </div>
                """,
                is_html=True
            )
            print(f"   ✓ Approval email sent to {user.email}")
        except Exception as e:
            print(f"   ⚠️ Could not send approval email: {e}")
        
        return redirect(url_for("admin_users"))
    
    except Exception as e:
        print(f"❌ Error approving user: {e}")
        return f"Error approving user: {str(e)}"

@app.route("/admin/reject/<int:user_id>")
def reject_user(user_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    
    try:
        user = User.query.get_or_404(user_id)
        email = user.email
        name = user.name
        
        db.session.delete(user)
        db.session.commit()
        
        print(f"❌ User rejected and deleted: {email}")
        
        try:
            send_email(
                email,
                "Registration Not Approved - Gautam Solar",
                f"""
                <div style="font-family:Arial;padding:20px;background:#f7fafc">
                    <div style="max-width:600px;margin:0 auto;background:white;padding:30px;border-radius:10px">
                        <h2 style="color:#f56565">Registration Not Approved</h2>
                        <p>Dear {name},</p>
                        <p>We regret to inform you that your registration has not been approved at this time.</p>
                        <p>If you have questions, please contact:</p>
                        <div style="background:#f7fafc;padding:15px;border-radius:5px;margin:15px 0">
                            <strong>Email:</strong> testing@gautamsolar.com<br>
                            <strong>Phone:</strong> +919599817214
                        </div>
                        <p style="margin-top:20px;color:#666;font-size:14px">
                            Thank you,<br>
                            <strong>Gautam Solar Team</strong>
                        </p>
                    </div>
                </div>
                """,
                is_html=True
            )
        except Exception as e:
            print(f"   ⚠️ Could not send rejection email: {e}")
        
        return redirect(url_for("admin_users"))
    
    except Exception as e:
        print(f"❌ Error rejecting user: {e}")
        return f"Error rejecting user: {str(e)}"

@app.route("/admin/certificates")
def admin_certificates():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    categories = ProductCategory.query.order_by(ProductCategory.order).all()
    return render_template("admin_certificates.html", categories=categories)

# ==================== CATEGORY MANAGEMENT ====================
@app.route("/admin/category/add", methods=["POST"])
def add_category():
    if "admin" not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        name = request.form.get("name")
        description = request.form.get("description", "")
        order = int(request.form.get("order", 0))
        
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'})
        
        category = ProductCategory(name=name, description=description, order=order)
        db.session.add(category)
        db.session.commit()
        
        return jsonify({'success': True, 'id': category.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route("/admin/category/<int:cat_id>/delete", methods=["POST"])
def delete_category(cat_id):
    if "admin" not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        category = ProductCategory.query.get_or_404(cat_id)
        db.session.delete(category)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# ==================== PRODUCT MANAGEMENT ====================
@app.route("/admin/product/add", methods=["POST"])
def add_product():
    if "admin" not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        category_id = int(request.form.get("category_id"))
        wattage = request.form.get("wattage")
        order = int(request.form.get("order", 0))
        availability = request.form.get("availability", "available")
        
        if not wattage:
            return jsonify({'success': False, 'error': 'Wattage is required'})
        
        product = Product(category_id=category_id, wattage=wattage, order=order, availability=availability)
        db.session.add(product)
        db.session.commit()
        
        return jsonify({'success': True, 'id': product.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route("/admin/product/<int:prod_id>/delete", methods=["POST"])
def delete_product(prod_id):
    if "admin" not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        product = Product.query.get_or_404(prod_id)
        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# ==================== DOCUMENT MANAGEMENT ====================
@app.route("/admin/document/add", methods=["POST"])
def add_document():
    if "admin" not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        product_id = int(request.form.get("product_id"))
        doc_type = request.form.get("doc_type")
        doc_name = request.form.get("doc_name", "")
        download_link = request.form.get("download_link")
        order = int(request.form.get("order", 0))
        
        if not doc_type or not download_link:
            return jsonify({'success': False, 'error': 'Document type and link are required'})
        
        if doc_type.lower() == "other" and doc_name:
            doc_type = doc_name
            doc_name = ""
        
        document = Document(
            product_id=product_id,
            doc_type=doc_type,
            doc_name=doc_name,
            download_link=download_link,
            order=order
        )
        db.session.add(document)
        db.session.commit()
        
        return jsonify({'success': True, 'id': document.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route("/admin/document/<int:doc_id>/delete", methods=["POST"])
def delete_document(doc_id):
    if "admin" not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        document = Document.query.get_or_404(doc_id)
        db.session.delete(document)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# ==================== COMPANY DOCUMENTS ====================
@app.route("/admin/company-docs")
def admin_company_docs():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    docs = CompanyDocument.query.all()
    return render_template("admin_company_docs.html", docs=docs)

@app.route("/admin/company-doc/add", methods=["POST"])
def add_company_doc():
    if "admin" not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        location = request.form.get("location")
        doc_type = request.form.get("doc_type")
        doc_name = request.form.get("doc_name", "")
        download_link = request.form.get("download_link")
        
        if not location or not doc_type or not download_link:
            return jsonify({'success': False, 'error': 'All fields are required'})
        
        if doc_type.lower() == "other" and doc_name:
            doc_type = doc_name
            doc_name = ""
        
        doc = CompanyDocument(location=location, doc_type=doc_type, doc_name=doc_name, download_link=download_link)
        db.session.add(doc)
        db.session.commit()
        
        return jsonify({'success': True, 'id': doc.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route("/admin/company-doc/<int:doc_id>/delete", methods=["POST"])
def delete_company_doc(doc_id):
    if "admin" not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        doc = CompanyDocument.query.get_or_404(doc_id)
        db.session.delete(doc)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))

# ==================== API ENDPOINTS ====================
@app.route("/api/notifications")
def api_notifications():
    notifications = HomeNotification.query.filter_by(is_active=True).order_by(HomeNotification.order).all()
    return jsonify([{
        'id': n.id,
        'title': n.title,
        'description': n.description,
        'type': n.notification_type
    } for n in notifications])

@app.route("/contact-info")
def contact_info():
    return jsonify({
        'company': 'Gautam Solar Pvt. Ltd.',
        'head_office': {
            'address': 'D 120-121 Okhla Industrial Area, Phase-1, New Delhi 110020',
            'gst': '07AAFCG5884Q2ZP'
        },
        'unit1': {
            'name': 'Unit 1 - Haridwar',
            'address': 'Plot No-67-70, SECTOR 8A, SIDCUL, IIE RANIPUR, HARIDWAR, UTTARAKHAND, 249403',
            'gst': '05AAFCG5884Q1ZU'
        },
        'unit2': {
            'name': 'Unit 2 - Bhiwani',
            'address': '7KM Milestone, Tosham Road, Dist. Bhiwani, Bawani Khera, Bhiwani, Haryana, 127032',
            'gst': '06AAFCG5884Q1ZS'
        },
        'contact_person': 'Sonu Panchal',
        'phone': '+919599817214',
        'email': 'testing@gautamsolar.com',
        'website': 'www.gautamsolar.com'
    })

# ==================== INITIALIZATION ====================
def init_db():
    with app.app_context():
        os.makedirs('database', exist_ok=True)
        
        try:
            Product.query.with_entities(Product.availability).first()
        except:
            print("⚠️  Adding availability column to Product table...")
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE product ADD COLUMN availability VARCHAR(20) DEFAULT 'available'"))
                conn.commit()
            print("✓ Availability column added!")
        
        try:
            CompanyDocument.query.with_entities(CompanyDocument.doc_name).first()
        except:
            print("⚠️  Adding doc_name column to CompanyDocument table...")
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE company_document ADD COLUMN doc_name VARCHAR(200)"))
                conn.commit()
            print("✓ doc_name column added!")
        
        db.create_all()
        print("✓ Database initialized!")
        
        if ProductCategory.query.count() == 0:
            print("✓ Adding sample data...")
            cat1 = ProductCategory(name="Mono PERC M10", description="High efficiency mono PERC modules", order=1)
            cat2 = ProductCategory(name="N-Type TOPCon G2B Bifacial", description="Next-gen bifacial modules", order=2)
            db.session.add_all([cat1, cat2])
            db.session.commit()
            
            prod1 = Product(category_id=cat1.id, wattage="530 Wp", order=1, availability="available")
            prod2 = Product(category_id=cat1.id, wattage="540 Wp", order=2, availability="limited")
            db.session.add_all([prod1, prod2])
            db.session.commit()
            
            doc1 = Document(product_id=prod1.id, doc_type="Datasheet", doc_name="Technical Datasheet", 
                          download_link="https://drive.google.com/file/d/sample1/view", order=1)
            doc2 = Document(product_id=prod1.id, doc_type="BIS Certificate", doc_name="BIS Certification", 
                          download_link="https://drive.google.com/file/d/sample2/view", order=2)
            db.session.add_all([doc1, doc2])
            db.session.commit()
            
            notif1 = HomeNotification(title="640Wp Panel Available", 
                                     description="New high-efficiency 640Wp solar panels now available!",
                                     notification_type="product_available", order=1, is_active=True)
            notif2 = HomeNotification(title="Summer Offers Live",
                                     description="Get up to 15% discount on bulk orders this summer!",
                                     notification_type="announcement", order=2, is_active=True)
            db.session.add_all([notif1, notif2])
            db.session.commit()
            
            print("✓ Sample data added!")

if __name__ == "__main__":
    init_db()
    print("\n" + "="*70)
    print("🚀 GAUTAM SOLAR PORTAL - SERVER STARTING")
    print("="*70)
    print("\n📋 Access URLs:")
    print("   🌐 Homepage:      http://127.0.0.1:5000/")
    print("   📖 About Us:      http://127.0.0.1:5000/about")
    print("   📞 Contact:       http://127.0.0.1:5000/contact")
    print("   🔐 Portal:        http://127.0.0.1:5000/portal")
    print("   👤 Login:         http://127.0.0.1:5000/login")
    print("   👑 Admin Panel:   http://127.0.0.1:5000/admin")
    print("\n👤 Admin Credentials:")
    print("   Email:    gautamsolarpvtltd@gmail.com")
    print("   Password: Skpanchaladmin123")
    print("\n✅ Features Active:")
    print("   ✓ About Us page with complete company info")
    print("   ✓ Contact page with all office locations")
    print("   ✓ Combined user/admin login page")
    print("   ✓ Registration with approval system")
    print("   ✓ Download protection (login required)")
    print("   ✓ Admin approval/rejection with emails")
    print("   ✓ Password reset with OTP")
    print("   ✓ Certificate management")
    print("   ✓ Company documents")
    print("   ✓ Portal access logging")
    print("\n⚠️  IMPORTANT:")
    print("   • Update ADMIN_PASSWORD with Gmail App Password for email notifications")
    print("   • Get App Password: https://myaccount.google.com/apppasswords")
    print("\n" + "="*70 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)