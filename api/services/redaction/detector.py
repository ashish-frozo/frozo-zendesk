"""
PII Detection Engine using Microsoft Presidio.

Implements:
- Pre-configured recognizers (email, phone, credit card, person, location)
- Custom recognizers (API keys, tokens, long hex strings)
- India-specific patterns (PAN, GSTIN - feature flagged)
- Configurable confidence thresholds
"""

import logging
from typing import List, Dict, Optional, Set
from presidio_analyzer import AnalyzerEngine, RecognizerResult, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider

logger = logging.getLogger(__name__)


class APIKeyRecognizer(PatternRecognizer):
    """Custom recognizer for API keys and tokens."""
    
    PATTERNS = [
        # Bearer tokens
        Pattern(name="bearer_token", regex=r"\b[Bb]earer\s+[A-Za-z0-9\-._~+/]+=*", score=0.9),
        
        # JWT-like tokens (header.payload.signature)
        Pattern(name="jwt_token", regex=r"\beyJ[A-Za-z0-9\-._~+/]+=*\.eyJ[A-Za-z0-9\-._~+/]+=*\.[A-Za-z0-9\-._~+/]+=*\b", score=0.95),
        
        # API key patterns
        Pattern(name="api_key_equals", regex=r"(?i)(api[_-]?key|apikey|api[_-]?token)\s*[=:]\s*['\"]?[A-Za-z0-9\-._~+/]{20,}['\"]?", score=0.85),
        
        # Authorization header values
        Pattern(name="auth_header", regex=r"(?i)(authorization|x-api-key)\s*:\s*[A-Za-z0-9\-._~+/]{20,}", score=0.85),
        
        # Long random strings (potential secrets)
        Pattern(name="long_random", regex=r"\b[A-Za-z0-9]{40,}\b", score=0.6),
        
        # Hex strings (potential keys)
        Pattern(name="hex_key", regex=r"\b[a-fA-F0-9]{32,}\b", score=0.65),
    ]
    
    def __init__(self):
        super().__init__(
            supported_entity="API_KEY",
            patterns=self.PATTERNS,
            name="API Key Recognizer",
            supported_language="en"
        )


class CreditCardRecognizer(PatternRecognizer):
    """Enhanced credit card recognizer for various formats."""
    
    PATTERNS = [
        # Standard format with dashes: 4532-1234-5678-9012
        Pattern(
            name="cc_dashed",
            regex=r"\b\d{4}-\d{4}-\d{4}-\d{4}\b",
            score=0.85
        ),
        # Format with spaces: 4532 1234 5678 9012
        Pattern(
            name="cc_spaced",
            regex=r"\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b",
            score=0.85
        ),
        # Partial card number (last 4 or last 8): ending in 9012 or 5678-9012
        Pattern(
            name="cc_partial",
            regex=r"(?:ending\s+in|last\s+\d+\s+digits?[:\s]+)(\d{4}(?:-\d{4})?)",
            score=0.9
        ),
    ]
    
    def __init__(self):
        super().__init__(
            supported_entity="CREDIT_CARD",
            patterns=self.PATTERNS,
            name="Enhanced Credit Card Recognizer",
            supported_language="en"
        )


class PhoneNumberRecognizer(PatternRecognizer):
    """Enhanced phone number recognizer for various formats."""
    
    PATTERNS = [
        # US format with country code: +1-555-123-4567
        Pattern(
            name="phone_us_international",
            regex=r"\+1-\d{3}-\d{3}-\d{4}\b",
            score=0.9
        ),
        # US format with parentheses: (555) 123-4567
        Pattern(
            name="phone_us_parens",
            regex=r"\(\d{3}\)\s*\d{3}-\d{4}\b",
            score=0.9
        ),
        # US format with dots: 555.123.4567
        Pattern(
            name="phone_us_dots",
            regex=r"\b\d{3}\.\d{3}\.\d{4}\b",
            score=0.85
        ),
        # US format with spaces: 555 123 4567
        Pattern(
            name="phone_us_spaces",
            regex=r"\b\d{3}\s\d{3}\s\d{4}\b",
            score=0.85
        ),
        # International format: +44 20 1234 5678
        Pattern(
            name="phone_international",
            regex=r"\+\d{1,3}\s?\d{2,4}\s?\d{4,5}\s?\d{4,5}\b",
            score=0.85
        ),
        # Generic format: 123-456-7890 or 1234567890
        Pattern(
            name="phone_generic",
            regex=r"\b\d{3}-\d{3}-\d{4}\b",
            score=0.8
        ),
    ]
    
    def __init__(self):
        super().__init__(
            supported_entity="PHONE_NUMBER",
            patterns=self.PATTERNS,
            name="Enhanced Phone Number Recognizer",
            supported_language="en"
        )


class IndianPANRecognizer(PatternRecognizer):
    """Recognizer for Indian PAN (Permanent Account Number)."""
    
    PATTERNS = [
        # PAN format: AAAAA9999A (5 letters, 4 digits, 1 letter)
        Pattern(name="pan_pattern", regex=r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", score=0.9),
    ]
    
    def __init__(self):
        super().__init__(
            supported_entity="INDIAN_PAN",
            patterns=self.PATTERNS,
            name="Indian PAN Recognizer",
            supported_language="en"
        )


class IndianGSTINRecognizer(PatternRecognizer):
    """Recognizer for Indian GSTIN (Goods and Services Tax Identification Number)."""
    
    PATTERNS = [
        # GSTIN format: 15 characters
        Pattern(name="gstin_pattern", regex=r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9][Z][0-9A-Z]\b", score=0.9),
    ]
    
    def __init__(self):
        super().__init__(
            supported_entity="INDIAN_GSTIN",
            patterns=self.PATTERNS,
            name="Indian GSTIN Recognizer",
            supported_language="en"
        )


class PIIDetector:
    """
    PII detection service using Presidio.
    
    Detects:
    - Email addresses
    - Phone numbers (US, international, India)
    - Credit card numbers
    - Person names (NER-based)
    - Locations
    - API keys and tokens
    - India-specific: PAN, GSTIN (optional)
    """
    
    def __init__(
        self,
        enable_indian_entities: bool = False,
        confidence_threshold: float = 0.5,
        entities_to_detect: Optional[List[str]] = None
    ):
        """
        Initialize PII detector.
        
        Args:
            enable_indian_entities: Enable PAN/GSTIN detection
            confidence_threshold: Minimum confidence score (0.0-1.0)
            entities_to_detect: List of entity types to detect, None = all
        """
        self.enable_indian_entities = enable_indian_entities
        self.confidence_threshold = confidence_threshold
        
        # Default entities to detect
        if entities_to_detect is None:
            self.entities_to_detect = [
                "EMAIL_ADDRESS",
                "PHONE_NUMBER",
                "CREDIT_CARD",
                "PERSON",
                "LOCATION",
                "API_KEY",
            ]
            if enable_indian_entities:
                self.entities_to_detect.extend(["INDIAN_PAN", "INDIAN_GSTIN"])
        else:
            self.entities_to_detect = entities_to_detect
        
        # Initialize NLP engine (spaCy)
        logger.info("Initializing NLP engine...")
        nlp_configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}]
        }
        provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
        nlp_engine = provider.create_engine()
        
        # Initialize analyzer with custom recognizers
        logger.info("Initializing Presidio analyzer...")
        self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
        
        # Add custom recognizers
        self.analyzer.registry.add_recognizer(APIKeyRecognizer())
        self.analyzer.registry.add_recognizer(CreditCardRecognizer())  # Enhanced CC detection
        self.analyzer.registry.add_recognizer(PhoneNumberRecognizer())  # Enhanced phone detection
        if enable_indian_entities:
            self.analyzer.registry.add_recognizer(IndianPANRecognizer())
            self.analyzer.registry.add_recognizer(IndianGSTINRecognizer())
        
        logger.info(f"PII Detector initialized. Detecting: {self.entities_to_detect}")
    
    def analyze(self, text: str, language: str = "en") -> List[RecognizerResult]:
        """
        Analyze text for PII entities.
        
        Args:
            text: Text to analyze
            language: Language code (default: en)
            
        Returns:
            List of RecognizerResult objects with detected entities
        """
        if not text or not text.strip():
            return []
        
        try:
            results = self.analyzer.analyze(
                text=text,
                language=language,
                entities=self.entities_to_detect,
                score_threshold=self.confidence_threshold
            )
            
            logger.debug(f"Detected {len(results)} PII entities in {len(text)} characters")
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return []
    
    def get_entity_counts(self, results: List[RecognizerResult]) -> Dict[str, int]:
        """
        Get counts of entities by type.
        
        Args:
            results: List of RecognizerResult objects
            
        Returns:
            Dictionary mapping entity type to count
        """
        counts = {}
        for result in results:
            entity_type = result.entity_type
            counts[entity_type] = counts.get(entity_type, 0) + 1
        return counts
    
    def get_low_confidence_entities(
        self, 
        results: List[RecognizerResult], 
        threshold: float = 0.7
    ) -> List[RecognizerResult]:
        """
        Get entities with confidence below threshold (for warnings).
        
        Args:
            results: List of RecognizerResult objects
            threshold: Confidence threshold for warnings
            
        Returns:
            List of low-confidence results
        """
        return [r for r in results if r.score < threshold]
    
    def format_detection_report(self, results: List[RecognizerResult]) -> Dict:
        """
        Format detection results into a report.
        
        Args:
            results: List of RecognizerResult objects
            
        Returns:
            Report dictionary with counts, warnings, and details
        """
        counts = self.get_entity_counts(results)
        low_confidence = self.get_low_confidence_entities(results)
        
        return {
            "total_detections": len(results),
            "entity_counts": counts,
            "low_confidence_count": len(low_confidence),
            "low_confidence_warnings": [
                {
                    "entity_type": r.entity_type,
                    "score": r.score,
                    "start": r.start,
                    "end": r.end
                }
                for r in low_confidence
            ]
        }


def create_detector(
    enable_indian_entities: bool = False,
    confidence_threshold: float = 0.5,
    entities_to_detect: Optional[List[str]] = None
) -> PIIDetector:
    """Factory function to create PII detector instance."""
    return PIIDetector(
        enable_indian_entities=enable_indian_entities,
        confidence_threshold=confidence_threshold,
        entities_to_detect=entities_to_detect
    )
