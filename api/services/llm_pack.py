"""
LLM Engineering Pack generation service.

Generates structured bug reports from sanitized ticket content using OpenAI GPT-4.
CRITICAL: Only sanitized content is sent to LLM - no raw PII.
"""

import logging
from typing import Dict, Optional
import json
from openai import OpenAI
from api.config import settings

logger = logging.getLogger(__name__)


# JSON Schema for LLM output validation
ENGINEERING_PACK_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "maxLength": 120},
        "steps_to_reproduce": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1
        },
        "expected_result": {"type": "string"},
        "actual_result": {"type": "string"},
        "environment": {
            "type": "object",
            "properties": {
                "app_version": {"type": ["string", "null"]},
                "browser": {"type": ["string", "null"]},
                "os": {"type": ["string", "null"]},
                "device": {"type": ["string", "null"]}
            }
        },
        "severity_suggestion": {
            "type": "string",
            "enum": ["blocker", "critical", "major", "minor", "trivial"]
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "tags": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["summary", "steps_to_reproduce", "expected_result", "actual_result", "severity_suggestion"]
}


class LLMPackService:
    """Service for generating structured engineering packs using LLM."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize LLM service.
        
        Args:
            api_key: OpenAI API key (uses settings if None)
            model: Model name
        """
        self.client = OpenAI(api_key=api_key or settings.openai_api_key)
        self.model = model
    
    def generate_pack(
        self,
        sanitized_text: str,
        ticket_subject: str,
        additional_context: Optional[Dict] = None
    ) -> Dict:
        """
        Generate engineering pack from sanitized ticket content.
        
        CRITICAL: sanitized_text must be PII-redacted. Never pass raw content.
        
        Args:
            sanitized_text: Redacted ticket content
            ticket_subject: Ticket subject line
            additional_context: Optional metadata (product version, etc.)
            
        Returns:
            Dictionary matching ENGINEERING_PACK_SCHEMA
        """
        try:
            # Build prompt
            prompt = self._build_prompt(sanitized_text, ticket_subject, additional_context)
            
            logger.info(f"Generating engineering pack with {self.model}")
            
            # Call OpenAI with structured output
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical writer creating structured bug reports for engineering teams. Extract key information and format it clearly."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=settings.openai_temperature,
                max_tokens=settings.openai_max_tokens
            )
            
            # Parse JSON response
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # Validate against schema
            if not self._validate_schema(result):
                logger.warning("LLM output doesn't match schema, using fallback")
                return self._generate_fallback(sanitized_text, ticket_subject)
            
            logger.info("Engineering pack generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"LLM pack generation failed: {e}")
            return self._generate_fallback(sanitized_text, ticket_subject)
    
    def _build_prompt(self, sanitized_text: str, subject: str, context: Optional[Dict]) -> str:
        """Build LLM prompt."""
        prompt = f"""Analyze this support ticket and create a structured bug report.

**Ticket Subject:** {subject}

**Sanitized Content:**
{sanitized_text}

"""
        
        if context:
            prompt += f"**Additional Context:** {json.dumps(context, indent=2)}\n\n"
        
        prompt += """Extract and format the following information as JSON:

{
  "summary": "Brief one-line summary (max 120 chars)",
  "steps_to_reproduce": ["Step 1", "Step 2", "Step 3"],
  "expected_result": "What should happen",
  "actual_result": "What actually happened",
  "environment": {
    "app_version": "version or null",
    "browser": "browser or null",
    "os": "operating system or null",
    "device": "device type or null"
  },
  "severity_suggestion": "blocker|critical|major|minor|trivial",
  "confidence": 0.0 to 1.0 (how confident you are in this extraction),
  "tags": ["relevant", "tags"]
}

Focus on actionable details. If information is missing, use null or best guess with lower confidence."""
        
        return prompt
    
    def _validate_schema(self, data: Dict) -> bool:
        """Validate output against schema (simplified)."""
        required = ["summary", "steps_to_reproduce", "expected_result", "actual_result", "severity_suggestion"]
        
        for field in required:
            if field not in data:
                return False
        
        if not isinstance(data["steps_to_reproduce"], list) or len(data["steps_to_reproduce"]) == 0:
            return False
        
        if len(data["summary"]) > 120:
            return False
        
        return True
    
    def _generate_fallback(self, sanitized_text: str, subject: str) -> Dict:
        """Generate deterministic fallback pack when LLM fails."""
        lines = sanitized_text.strip().split('\n')
        
        # Heuristic extraction
        steps = []
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if any(word in line_lower for word in ['step', 'then', 'when', 'click', 'open', 'go to']):
                steps.append(line.strip())
        
        if not steps:
            steps = ["Unable to extract steps automatically", "Please review original ticket"]
        
        return {
            "summary": subject[:120] if subject else "Support escalation",
            "steps_to_reproduce": steps[:5],
            "expected_result": "Expected behavior not specified",
            "actual_result": "Issue reported by customer",
            "environment": {
                "app_version": None,
                "browser": None,
                "os": None,
                "device": None
            },
            "severity_suggestion": "major",
            "confidence": 0.3,
            "tags": ["support-escalation", "needs-review"]
        }


def create_llm_pack_service() -> LLMPackService:
    """Factory function to create LLM pack service."""
    return LLMPackService()
