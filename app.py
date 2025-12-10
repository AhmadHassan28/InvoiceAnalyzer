from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from dotenv import load_dotenv
import mlflow
import os

import mlflow
import os

# Configure DagsHub MLflow tracking
os.environ['MLFLOW_TRACKING_USERNAME'] = 'l230861'
os.environ['MLFLOW_TRACKING_PASSWORD'] = '95c0b9c5cbeb5e8a79f5dfd125cc78bf9bfdaf3d'

mlflow.set_tracking_uri("https://dagshub.com/l230861/invoice-analyzer.mlflow")
mlflow.set_experiment("production-invoice-processing")

print("✅ MLflow cloud tracking enabled")

# Load environment variables from .env file
load_dotenv()

# Import after loading env variables
from model_engine import InvoiceAnalyzer

app = Flask(__name__)

# Configuration from environment variables
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize AI Engine
print("🚀 Loading OCR Engine...")
analyzer = InvoiceAnalyzer()
print("✅ OCR Engine Ready!")

# ==================== DATABASE MODELS ====================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    documents = db.relationship('Document', backref='owner', lazy=True, cascade='all, delete-orphan')

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    document_type = db.Column(db.String(50))  # invoice, receipt, bill
    total_amount = db.Column(db.Float)
    currency = db.Column(db.String(10))
    vendor_name = db.Column(db.String(200))
    extracted_text = db.Column(db.Text)
    confidence_score = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Create tables
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== HELPER FUNCTIONS ====================

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== ROUTES ====================

@app.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        # Create new user
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing'))

@app.route('/dashboard')
@login_required
def dashboard():
    recent_docs = Document.query.filter_by(user_id=current_user.id)\
        .order_by(Document.upload_date.desc()).limit(5).all()
    
    # Calculate stats
    total_docs = Document.query.filter_by(user_id=current_user.id).count()
    total_amount = db.session.query(db.func.sum(Document.total_amount))\
        .filter_by(user_id=current_user.id).scalar() or 0
    
    return render_template('dashboard.html', 
                         recent_docs=recent_docs,
                         total_docs=total_docs,
                         total_amount=total_amount)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)
    
    # Track with MLflow Cloud
    with mlflow.start_run(run_name=f"invoice_processing_{timestamp}"):
        try:
            # Log input parameters
            mlflow.log_param("filename", unique_filename)
            mlflow.log_param("user_id", current_user.id)
            mlflow.log_param("upload_time", timestamp)
            
            # Process invoice
            result = analyzer.analyze_document(filepath)
            
            # Log results as metrics
            mlflow.log_metric("total_amount", result['total_amount'])
            mlflow.log_metric("confidence_score", result['confidence'])
            
            # Log results as parameters
            mlflow.log_param("vendor_name", result['vendor_name'])
            mlflow.log_param("currency", result['currency'])
            mlflow.log_param("document_type", result['document_type'])
            
            # Save to database
            new_doc = Document(
                filename=unique_filename,
                document_type=result['document_type'],
                total_amount=result['total_amount'],
                currency=result['currency'],
                vendor_name=result['vendor_name'],
                extracted_text=result['text'],
                confidence_score=result['confidence'],
                user_id=current_user.id
            )
            
            db.session.add(new_doc)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'data': result,
                'doc_id': new_doc.id
            })
            
        except Exception as e:
            mlflow.log_param("error", str(e))
            mlflow.log_param("status", "failed")
            return jsonify({'error': str(e)}), 500


@app.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    documents = Document.query.filter_by(user_id=current_user.id)\
        .order_by(Document.upload_date.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    
    return render_template('history.html', documents=documents)

@app.route('/document/<int:doc_id>')
@login_required
def view_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    
    # Security check
    if doc.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    return jsonify({
        'filename': doc.filename,
        'upload_date': doc.upload_date.strftime('%Y-%m-%d %H:%M'),
        'document_type': doc.document_type,
        'total_amount': doc.total_amount,
        'currency': doc.currency,
        'vendor_name': doc.vendor_name,
        'text': doc.extracted_text,
        'confidence': doc.confidence_score
    })

@app.route('/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    
    if doc.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Delete file
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], doc.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    
    db.session.delete(doc)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/stats')
@login_required
def get_stats():
    # Monthly spending
    monthly_data = db.session.query(
        db.func.strftime('%Y-%m', Document.upload_date).label('month'),
        db.func.sum(Document.total_amount).label('total')
    ).filter_by(user_id=current_user.id)\
     .group_by('month')\
     .order_by('month')\
     .limit(12).all()
    
    return jsonify({
        'monthly': [{'month': m[0], 'total': float(m[1] or 0)} for m in monthly_data]
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)