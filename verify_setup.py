import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("🔍 VERIFYING COMPLETE SETUP")
print("=" * 60)

# Check 1: .env file exists
print("\n📁 1. Checking .env file...")
if os.path.exists('.env'):
    print("   ✅ .env file found")
else:
    print("   ❌ .env file NOT found! Create it first!")
    exit()

# Check 2: Environment variables loaded
print("\n🔐 2. Checking environment variables...")
db_url = os.getenv('DATABASE_URL')
secret_key = os.getenv('SECRET_KEY')

if db_url:
    # Show partial URL (hide password)
    if '@' in db_url:
        host_part = db_url.split('@')[1].split('/')[0]
        print(f"   ✅ DATABASE_URL: ...@{host_part}/...")
    else:
        print("   ⚠️  DATABASE_URL format looks wrong!")
else:
    print("   ❌ DATABASE_URL not set!")
    exit()

if secret_key:
    print(f"   ✅ SECRET_KEY: {secret_key[:20]}...")
else:
    print("   ❌ SECRET_KEY not set!")

# Check 3: Try importing Flask app
print("\n🌐 3. Testing Flask app import...")
try:
    from app import app, db, User, Document
    print("   ✅ Flask app imported successfully")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    exit()

# Check 4: Database connection
print("\n🗄️  4. Testing database connection...")
with app.app_context():
    try:
        connection = db.engine.connect()
        print(f"   ✅ Connected to: {db.engine.url.drivername}")
        print(f"   ✅ Host: {db.engine.url.host}")
        print(f"   ✅ Database: {db.engine.url.database}")
        connection.close()
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        exit()

# Check 5: Tables exist
    print("\n📊 5. Checking database tables...")
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    if 'user' in tables and 'document' in tables:
        print(f"   ✅ Required tables found: {', '.join(tables)}")
    else:
        print(f"   ⚠️  Found tables: {tables}")
        print("   Creating missing tables...")
        db.create_all()
        print("   ✅ Tables created!")

# Check 6: Count records
    print("\n📈 6. Checking data...")
    user_count = User.query.count()
    doc_count = Document.query.count()
    print(f"   👥 Users in database: {user_count}")
    print(f"   📄 Documents in database: {doc_count}")

# Check 7: Upload folder
print("\n📁 7. Checking upload folder...")
upload_folder = os.getenv('UPLOAD_FOLDER', 'uploads')
if os.path.exists(upload_folder):
    file_count = len(os.listdir(upload_folder))
    print(f"   ✅ Upload folder exists: {upload_folder}/")
    print(f"   📦 Files in folder: {file_count}")
else:
    print(f"   ⚠️  Upload folder not found, creating...")
    os.makedirs(upload_folder)
    print(f"   ✅ Created: {upload_folder}/")

# Check 8: Tesseract
print("\n🔍 8. Checking Tesseract OCR...")
try:
    import pytesseract
    version = pytesseract.get_tesseract_version()
    print(f"   ✅ Tesseract installed: v{version}")
except:
    print("   ⚠️  Tesseract not found or not configured")
    print("   Note: You'll need this for OCR to work")

print("\n" + "=" * 60)
print("✅ SETUP VERIFICATION COMPLETE!")
print("=" * 60)
print("\nYou can now run: python app.py")