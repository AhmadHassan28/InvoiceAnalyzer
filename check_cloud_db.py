from app import app, db, User, Document

with app.app_context():
    print("=" * 50)
    print("🌐 CLOUD DATABASE STATUS")
    print("=" * 50)
    
    # Check connection
    try:
        db.engine.connect()
        print("✅ Connected to PostgreSQL!")
        print(f"📍 Host: {db.engine.url.host}")
        print(f"🗄️  Database: {db.engine.url.database}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        exit()
    
    # Count records
    user_count = User.query.count()
    doc_count = Document.query.count()
    
    print(f"\n👥 Total Users: {user_count}")
    print(f"📄 Total Documents: {doc_count}")
    
    # Show all users
    if user_count > 0:
        print("\n" + "=" * 50)
        print("REGISTERED USERS:")
        print("=" * 50)
        for user in User.query.all():
            docs = Document.query.filter_by(user_id=user.id).count()
            print(f"\n👤 ID: {user.id}")
            print(f"   Username: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Joined: {user.created_at}")
            print(f"   Documents: {docs}")
    else:
        print("\n⚠️  No users registered yet!")
    
    # Show all documents
    if doc_count > 0:
        print("\n" + "=" * 50)
        print("UPLOADED DOCUMENTS:")
        print("=" * 50)
        for doc in Document.query.all():
            print(f"\n📝 ID: {doc.id}")
            print(f"   File: {doc.filename}")
            print(f"   Owner: {doc.owner.username}")
            print(f"   Type: {doc.document_type}")
            print(f"   Amount: {doc.currency} {doc.total_amount}")
            print(f"   Confidence: {doc.confidence_score * 100:.0f}%")
    else:
        print("\n⚠️  No documents uploaded yet!")
    
    print("\n" + "=" * 50)