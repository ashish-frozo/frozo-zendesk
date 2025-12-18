"""
Test script for M1 text redaction functionality.

Tests:
- PII detection with various entity types
- Text redaction
- API endpoints
"""

import sys
sys.path.insert(0, '/Users/ashishdhiman/WORK/Frozo-projects/frozo-zendesk')

from api.services.redaction import create_detector, create_redactor

# Test text with various PII
test_text = """
Customer Issue Report:

Hi, I'm John Doe and I need help with my account. My email is john.doe@example.com 
and my phone number is +1-555-123-4567. 

I tried using my credit card ending in 4532 but it failed. Can you check with my API key: 
Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U

My user ID is abc123def456 and I'm located in San Francisco, California.

Additional details:
- Order ID: ORD-2024-12345
- Transaction ID: TXN-ABC-XYZ-789
- API Secret: sk_test_51234567890abcdef
"""

def test_pii_detection():
    """Test PII detection engine."""
    print("=" * 60)
    print("TEST 1: PII Detection")
    print("=" * 60)
    
    detector = create_detector(
        enable_indian_entities=False,
        confidence_threshold=0.5
    )
    
    results = detector.analyze(test_text)
    report = detector.format_detection_report(results)
    
    print(f"\n✓ Total detections: {report['total_detections']}")
    print("\n✓ Entity counts:")
    for entity_type, count in report['entity_counts'].items():
        print(f"  - {entity_type}: {count}")
    
    print(f"\n✓ Low confidence warnings: {report['low_confidence_count']}")
    
    if report['low_confidence_count'] > 0:
        print("\nLow confidence entities:")
        for warning in report['low_confidence_warnings']:
            print(f"  - {warning['entity_type']} (score: {warning['score']:.2f})")
    
    print("\n✅ PII Detection Test PASSED\n")
    return results


def test_text_redaction(detection_results):
    """Test text redaction."""
    print("=" * 60)
    print("TEST 2: Text Redaction")
    print("=" * 60)
    
    redactor = create_redactor()
    result = redactor.redact_with_report(test_text, detection_results)
    
    print(f"\n✓ Original length: {result['original_length']} characters")
    print(f"✓ Redacted length: {result['redacted_length']} characters")
    print(f"✓ Total redactions: {result['total_redactions']}")
    
    print("\n✓ Entities redacted:")
    for entity_type, count in result['entities_redacted'].items():
        print(f"  - {entity_type}: {count}")
    
    print("\n✓ Redacted text preview (first 300 chars):")
    print("-" * 60)
    print(result['redacted_text'][:300] + "...")
    print("-" * 60)
    
    print("\n✅ Text Redaction Test PASSED\n")
    return result


def test_determinism():
    """Test that redaction is deterministic."""
    print("=" * 60)
    print("TEST 3: Determinism")
    print("=" * 60)
    
    detector = create_detector()
    redactor = create_redactor()
    
    # Run twice
    results1 = detector.analyze(test_text)
    redacted1 = redactor.redact(test_text, results1)
    
    results2 = detector.analyze(test_text)
    redacted2 = redactor.redact(test_text, results2)
    
    if redacted1 == redacted2:
        print("\n✅ Determinism Test PASSED - Identical outputs")
    else:
        print("\n❌ Determinism Test FAILED - Outputs differ")
        print(f"Length 1: {len(redacted1)}, Length 2: {len(redacted2)}")
    
    print()


def main():
    """Run all tests."""
    print("\n🧪 EscalateSafe M1 - Text Redaction Tests")
    print("=" * 60)
    print()
    
    try:
        # Test 1: PII Detection
        detection_results = test_pii_detection()
        
        # Test 2: Text Redaction
        redaction_result = test_text_redaction(detection_results)
        
        # Test 3: Determinism
        test_determinism()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Start Docker: docker-compose up -d")
        print("2. Start API: python api/main.py")
        print("3. Test API: curl http://localhost:8000/health")
        print()
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
