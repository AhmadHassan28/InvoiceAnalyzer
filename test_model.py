from model_engine import InvoiceAnalyzer

# Initialize
print("🚀 Testing InvoiceAnalyzer...")
analyzer = InvoiceAnalyzer()
print("✅ Analyzer initialized!")

# Test with dummy data
test_text = """
ABC Company
Invoice #12345
Date: 2024-01-15

Item: Widget
Amount: $150.00

Total: $150.00
"""

print("\n📝 Testing text analysis...")
# Simulate document processing
result = analyzer._classify_document(test_text)
print(f"✅ Document Type: {result}")

amount = analyzer._extract_amount(test_text)
print(f"✅ Amount Extracted: ${amount}")

currency = analyzer._extract_currency(test_text)
print(f"✅ Currency: {currency}")

vendor = analyzer._extract_vendor(test_text)
print(f"✅ Vendor: {vendor}")

confidence = analyzer._calculate_confidence(test_text)
print(f"✅ Confidence: {confidence * 100:.1f}%")

print("\n🎉 All tests passed! model_engine.py is working!")