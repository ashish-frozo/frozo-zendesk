"""
Leak prevention test suite.

Scans exported Jira issues and Slack messages for residual PII patterns.
HARD GATE: Zero PII matches required for pilot readiness.
"""

import re
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


# PII detection patterns (for verification)
PII_PATTERNS = {
    "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    "phone_us": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    "phone_intl": r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
    "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
    "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
    "api_key_bearer": r'\b[Bb]earer\s+[A-Za-z0-9\-._~+/]{20,}\b',
    "jwt": r'\beyJ[A-Za-z0-9\-._~+/]+=*\.eyJ[A-Za-z0-9\-._~+/]+=*\.[A-Za-z0-9\-._~+/]+=*\b',
    "api_key_pattern": r'(api[_-]?key|apikey|api[_-]?token)\s*[=:]\s*[\'"]?[A-Za-z0-9\-._~+/]{20,}',
    "long_hex": r'\b[a-fA-F0-9]{32,}\b',
}


def scan_for_pii(text: str) -> List[Tuple[str, List[str]]]:
    """
    Scan text for PII patterns.
    
    Args:
        text: Text to scan
        
    Returns:
        List of (pattern_name, matches) tuples
    """
    findings = []
    
    for pattern_name, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            findings.append((pattern_name, matches))
    
    return findings


def test_jira_issue_leak(issue_data: Dict) -> Dict:
    """
    Test Jira issue for PII leakage.
    
    Args:
        issue_data: Jira issue dict with summary, description, comments
        
    Returns:
        Test result dict
    """
    text_to_scan = ""
    
    if "summary" in issue_data:
        text_to_scan += issue_data["summary"] + "\n"
    
    if "description" in issue_data:
        text_to_scan += issue_data["description"] + "\n"
    
    if "comments" in issue_data:
        for comment in issue_data["comments"]:
            text_to_scan += comment.get("body", "") + "\n"
    
    findings = scan_for_pii(text_to_scan)
    
    return {
        "jira_key": issue_data.get("key", "unknown"),
        "passed": len(findings) == 0,
        "findings": findings,
        "total_matches": sum(len(matches) for _, matches in findings)
    }


def test_slack_message_leak(message_data: Dict) -> Dict:
    """
    Test Slack message for PII leakage.
    
    Args:
        message_data: Slack message dict with text, blocks
        
    Returns:
        Test result dict
    """
    text_to_scan = message_data.get("text", "")
    
    # Also scan blocks
    if "blocks" in message_data:
        for block in message_data["blocks"]:
            if "text" in block:
                text_to_scan += " " + str(block["text"])
            if "fields" in block:
                for field in block["fields"]:
                    text_to_scan += " " + str(field.get("text", ""))
    
    findings = scan_for_pii(text_to_scan)
    
    return {
        "message_id": message_data.get("ts", "unknown"),
        "passed": len(findings) == 0,
        "findings": findings,
        "total_matches": sum(len(matches) for _, matches in findings)
    }


def run_leak_prevention_tests(test_data: Dict) -> Dict:
    """
    Run full leak prevention test suite.
    
    Args:
        test_data: Dict with 'jira_issues' and 'slack_messages' lists
        
    Returns:
        Test results summary
    """
    results = {
        "jira_tests": [],
        "slack_tests": [],
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "total_pii_matches": 0
    }
    
    # Test Jira issues
    for issue in test_data.get("jira_issues", []):
        result = test_jira_issue_leak(issue)
        results["jira_tests"].append(result)
        results["total_tests"] += 1
        
        if result["passed"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
            results["total_pii_matches"] += result["total_matches"]
    
    # Test Slack messages
    for message in test_data.get("slack_messages", []):
        result = test_slack_message_leak(message)
        results["slack_tests"].append(result)
        results["total_tests"] += 1
        
        if result["passed"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
            results["total_pii_matches"] += result["total_matches"]
    
    # Overall pass/fail
    results["all_passed"] = results["failed"] == 0
    
    return results


def print_test_report(results: Dict):
    """Print formatted test report."""
    print("\n" + "="*60)
    print("LEAK PREVENTION TEST RESULTS")
    print("="*60)
    print(f"\nTotal Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Total PII Matches: {results['total_pii_matches']}")
    
    if results["all_passed"]:
        print("\n✅ ALL TESTS PASSED - No PII leakage detected")
    else:
        print("\n❌ TESTS FAILED - PII leakage detected!")
        
        # Print details
        print("\nFailed Tests:")
        for test in results["jira_tests"]:
            if not test["passed"]:
                print(f"\n  Jira Issue: {test['jira_key']}")
                for pattern_name, matches in test["findings"]:
                    print(f"    - {pattern_name}: {len(matches)} matches")
                    for match in matches[:3]:  # Show first 3
                        print(f"      → {match[:50]}...")
        
        for test in results["slack_tests"]:
            if not test["passed"]:
                print(f"\n  Slack Message: {test['message_id']}")
                for pattern_name, matches in test["findings"]:
                    print(f"    - {pattern_name}: {len(matches)} matches")
    
    print("\n" + "="*60)
    
    return results["all_passed"]
