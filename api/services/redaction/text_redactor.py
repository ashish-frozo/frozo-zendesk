"""
Text redaction service.

Takes PII detection results and redacts sensitive information from text.
Implements configurable redaction policies.
"""

import logging
from typing import List, Dict, Optional
from presidio_analyzer import RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = logging.getLogger(__name__)


class RedactionPolicy:
    """Redaction policy configuration."""
    
    # Default redaction templates
    DEFAULT_TEMPLATES = {
        "EMAIL_ADDRESS": "[EMAIL_REDACTED]",
        "PHONE_NUMBER": "[PHONE_REDACTED]",
        "CREDIT_CARD": "[CREDIT_CARD_REDACTED]",
        "PERSON": "[NAME_REDACTED]",
        "LOCATION": "[LOCATION_REDACTED]",
        "API_KEY": "[API_KEY_REDACTED]",
        "INDIAN_PAN": "[PAN_REDACTED]",
        "INDIAN_GSTIN": "[GSTIN_REDACTED]",
    }
    
    def __init__(self, custom_templates: Optional[Dict[str, str]] = None):
        """
        Initialize redaction policy.
        
        Args:
            custom_templates: Optional custom redaction templates by entity type
        """
        self.templates = self.DEFAULT_TEMPLATES.copy()
        if custom_templates:
            self.templates.update(custom_templates)
    
    def get_template(self, entity_type: str) -> str:
        """Get redaction template for entity type."""
        return self.templates.get(entity_type, f"[{entity_type}_REDACTED]")


class TextRedactor:
    """
    Text redaction service.
    
    Applies redaction to text based on PII detection results.
    """
    
    def __init__(self, policy: Optional[RedactionPolicy] = None):
        """
        Initialize text redactor.
        
        Args:
            policy: Redaction policy (uses default if None)
        """
        self.policy = policy or RedactionPolicy()
        self.anonymizer = AnonymizerEngine()
    
    def redact(self, text: str, detection_results: List[RecognizerResult]) -> str:
        """
        Redact PII from text.
        
        Args:
            text: Original text
            detection_results: PII detection results from Presidio
            
        Returns:
            Redacted text with PII replaced by templates
        """
        if not text or not detection_results:
            return text
        
        try:
            # Build operators configuration
            operators = {}
            for result in detection_results:
                entity_type = result.entity_type
                if entity_type not in operators:
                    operators[entity_type] = OperatorConfig(
                        "replace",
                        {"new_value": self.policy.get_template(entity_type)}
                    )
            
            # Anonymize text
            anonymized = self.anonymizer.anonymize(
                text=text,
                analyzer_results=detection_results,
                operators=operators
            )
            
            return anonymized.text
            
        except Exception as e:
            logger.error(f"Error redacting text: {e}")
            # Fallback: return original text (fail-safe, but logs error)
            return text
    
    def redact_with_report(
        self, 
        text: str, 
        detection_results: List[RecognizerResult]
    ) -> Dict:
        """
        Redact text and generate detailed report.
        
        Args:
            text: Original text
            detection_results: PII detection results
            
        Returns:
            Dictionary with:
            - redacted_text: Sanitized text
            - original_length: Length of original text
            - redacted_length: Length of redacted text
            - entities_redacted: Count by entity type
            - redaction_positions: List of redaction positions
        """
        redacted_text = self.redact(text, detection_results)
        
        # Calculate entity counts
        entity_counts = {}
        redaction_positions = []
        
        for result in detection_results:
            entity_type = result.entity_type
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
            
            redaction_positions.append({
                "entity_type": entity_type,
                "start": result.start,
                "end": result.end,
                "original_length": result.end - result.start,
                "redacted_value": self.policy.get_template(entity_type)
            })
        
        return {
            "redacted_text": redacted_text,
            "original_length": len(text),
            "redacted_length": len(redacted_text),
            "entities_redacted": entity_counts,
            "redaction_positions": redaction_positions,
            "total_redactions": len(detection_results)
        }
    
    def generate_diff_view(
        self, 
        original: str, 
        redacted: str, 
        detection_results: List[RecognizerResult]
    ) -> List[Dict]:
        """
        Generate diff view segments for UI display.
        
        Args:
            original: Original text
            redacted: Redacted text
            detection_results: PII detection results
            
        Returns:
            List of segments with:
            - text: Segment text
            - type: 'original' | 'redacted' | 'unchanged'
            - entity_type: Entity type (if redacted)
        """
        if not detection_results:
            return [{"text": original, "type": "unchanged", "entity_type": None}]
        
        segments = []
        last_end = 0
        
        # Sort results by start position
        sorted_results = sorted(detection_results, key=lambda r: r.start)
        
        for result in sorted_results:
            # Add unchanged text before this redaction
            if result.start > last_end:
                segments.append({
                    "text": original[last_end:result.start],
                    "type": "unchanged",
                    "entity_type": None
                })
            
            # Add redacted segment
            segments.append({
                "text": self.policy.get_template(result.entity_type),
                "type": "redacted",
                "entity_type": result.entity_type,
                "original_text": original[result.start:result.end]  # For debugging only
            })
            
            last_end = result.end
        
        # Add remaining unchanged text
        if last_end < len(original):
            segments.append({
                "text": original[last_end:],
                "type": "unchanged",
                "entity_type": None
            })
        
        return segments


def create_redactor(custom_templates: Optional[Dict[str, str]] = None) -> TextRedactor:
    """Factory function to create text redactor instance."""
    policy = RedactionPolicy(custom_templates) if custom_templates else None
    return TextRedactor(policy=policy)
