import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
import pdf2image
import os

# WINDOWS USERS: Uncomment and update path below
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class InvoiceAnalyzer:
    """
    AI-powered document analyzer using OCR and pattern matching.
    """
    
    def __init__(self):
        self.currency_symbols = {
            '$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY',
            '₹': 'INR', 'Rs': 'INR', 'PKR': 'PKR'
        }
        
        self.document_keywords = {
            'invoice': ['invoice', 'bill', 'inv no', 'invoice no', 'invoice #'],
            'receipt': ['receipt', 'payment received', 'paid'],
            'bill': ['bill', 'statement', 'amount due']
        }
    
    def analyze_document(self, filepath):
        """Main analysis function"""
        try:
            # Extract text based on file type
            if filepath.lower().endswith('.pdf'):
                text = self._extract_text_from_pdf(filepath)
            else:
                text = self._extract_text_from_image(filepath)
            
            if not text.strip():
                raise ValueError("No text could be extracted from document")
            
            # DEBUG: Print extracted text (remove in production)
            print("="*60)
            print("🔍 EXTRACTED TEXT:")
            print("="*60)
            print(text)
            print("="*60)
            
            # Analyze extracted text
            doc_type = self._classify_document(text)
            amount = self._extract_amount(text)
            currency = self._extract_currency(text)
            vendor = self._extract_vendor(text)
            confidence = self._calculate_confidence(text)
            
            return {
                'document_type': doc_type,
                'total_amount': amount,
                'currency': currency,
                'vendor_name': vendor,
                'text': text,
                'confidence': confidence,
                'status': 'success'
            }
        
        except Exception as e:
            return {
                'document_type': 'unknown',
                'total_amount': 0.0,
                'currency': 'USD',
                'vendor_name': 'Unknown',
                'text': '',
                'confidence': 0.0,
                'status': 'error',
                'error': str(e)
            }
    
    def _extract_text_from_image(self, filepath):
        """Extract text from image using OCR"""
        # Read and preprocess image
        img = cv2.imread(filepath)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding for better OCR
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        # Apply slight blur to reduce noise
        gray = cv2.medianBlur(gray, 3)
        
        # OCR with Tesseract
        text = pytesseract.image_to_string(gray)
        return text
    
    def _extract_text_from_pdf(self, filepath):
        """Extract text from PDF"""
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_path(filepath, dpi=300, first_page=1, last_page=1)
            
            if not images:
                return ""
            
            # Process first page only (for speed)
            text = pytesseract.image_to_string(images[0])
            return text
        except Exception as e:
            print(f"PDF extraction error: {e}")
            return ""
    
    def _classify_document(self, text):
        """Classify document type based on keywords"""
        text_lower = text.lower()
        
        scores = {}
        for doc_type, keywords in self.document_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[doc_type] = score
        
        # Return type with highest score
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return 'invoice'  # Default
    
    def _extract_amount(self, text):
        """Extract monetary amounts using IMPROVED regex with priority"""
        
        # PRIORITY 1: Look for explicit "Total Amount" or "Total" labels
        # These are most likely to be the final amount
        priority_patterns = [
            r'total\s*amount[\s:]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # Total Amount: $5,632
            r'total[\s:]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',           # Total: $5,632
            r'amount\s*due[\s:]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',   # Amount Due: $5,632
            r'grand\s*total[\s:]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # Grand Total: $5,632
        ]
        
        # Try priority patterns first
        for pattern in priority_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount_str = match.group(1).replace(',', '').replace(' ', '')
                    amount = float(amount_str)
                    print(f"✅ Found priority amount: ${amount:,.2f} (pattern: {pattern[:30]}...)")
                    return amount
                except:
                    continue
        
        # PRIORITY 2: Look for amounts with "Total" keyword nearby
        # Extract all amounts and find those near "total" keyword
        amounts_with_context = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if 'total' in line_lower:
                # Extract numbers from this line and surrounding lines
                context_lines = lines[max(0, i-1):min(len(lines), i+2)]
                context_text = ' '.join(context_lines)
                
                # Find all amounts in context
                amount_pattern = r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
                matches = re.finditer(amount_pattern, context_text)
                
                for match in matches:
                    try:
                        amount_str = match.group(1).replace(',', '').replace(' ', '')
                        amount = float(amount_str)
                        if amount > 100:  # Filter out small numbers (likely not totals)
                            amounts_with_context.append(amount)
                            print(f"💡 Found amount near 'total': ${amount:,.2f}")
                    except:
                        continue
        
        if amounts_with_context:
            result = max(amounts_with_context)
            print(f"✅ Selected max from context amounts: ${result:,.2f}")
            return result
        
        # FALLBACK: Extract all amounts and return the largest
        print("⚠️  Using fallback: extracting all amounts and selecting max")
        
        all_amounts = []
        patterns = [
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $5,632.00 or $5,632
            r'(\d{1,3}(?:,\d{3})+)',                    # 5,632 (with comma)
            r'(?:Rs\.?|PKR)\s*(\d+[,.]?\d*)',          # Rs 5632
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount_str = match.group(1).replace(',', '').replace(' ', '')
                    amount = float(amount_str)
                    if amount > 10:  # Filter tiny amounts
                        all_amounts.append(amount)
                        print(f"   Found: ${amount:,.2f}")
                except:
                    continue
        
        if all_amounts:
            result = max(all_amounts)
            print(f"✅ Selected max from all amounts: ${result:,.2f}")
            return result
        
        print("❌ No amounts found")
        return 0.0
    
    def _extract_currency(self, text):
        """Extract currency from text"""
        for symbol, code in self.currency_symbols.items():
            if symbol in text:
                return code
        return 'USD'  # Default
    
    def _extract_vendor(self, text):
        """Extract vendor/company name (first line usually)"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Filter out common noise
        noise_words = ['invoice', 'receipt', 'bill', 'tax', 'date']
        
        for line in lines[:5]:  # Check first 5 lines
            line_lower = line.lower()
            if len(line) > 3 and not any(word in line_lower for word in noise_words):
                # Likely the vendor name
                return line[:100]  # Limit length
        
        return 'Unknown Vendor'
    
    def _calculate_confidence(self, text):
        """Calculate confidence score based on text quality"""
        if not text:
            return 0.0
        
        # Factors for confidence
        has_amount = bool(re.search(r'\d+\.?\d*', text))
        has_keywords = any(kw in text.lower() for keywords in self.document_keywords.values() for kw in keywords)
        text_length = len(text.split())
        
        confidence = 0.0
        if has_amount:
            confidence += 0.4
        if has_keywords:
            confidence += 0.3
        if text_length > 20:
            confidence += 0.3
        
        return min(confidence, 1.0)
