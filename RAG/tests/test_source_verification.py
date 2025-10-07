import json
import pytest
import requests
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class SourceTestCase:
    """Represents a test case with question and expected source"""
    question: str
    expected_source: str
    language: str = "EN"
    model: str = "meta.llama-3.3-70b-instruct"

def get_api_response(test_case: SourceTestCase) -> Dict[str, Any]:
    """Make API call and return the last chunk containing sources"""
    url = "http://localhost:9000/ask"
    headers = {"Content-Type": "application/json"}
    data = {
        "message": test_case.question,
        "genModel": test_case.model,
        "language": test_case.language,
        "conversation": []
    }
    
    response = requests.post(url, headers=headers, json=data, stream=True)
    last_chunk = None
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data:'):
                try:
                    chunk = json.loads(line[5:])  # Remove 'data:' prefix
                    if chunk.get('type') == 'done':
                        last_chunk = chunk
                except json.JSONDecodeError:
                    continue
    
    return last_chunk

def verify_sources(sources: List[Dict[str, Any]], expected_source: str) -> bool:
    """Verify if expected source is present in any of the source breadcrumbs"""
    for source in sources:
        breadcrumb = source.get('metadata', {}).get('breadcrumb', '')
        if expected_source in breadcrumb:
            return True
    return False

def format_sources_for_error(sources: List[Dict[str, Any]]) -> str:
    """Format sources for error message"""
    breadcrumbs = []
    for source in sources:
        breadcrumb = source.get('metadata', {}).get('breadcrumb', '')
        breadcrumbs.append(f"- {breadcrumb}")
    return "\n".join(breadcrumbs)

# Test cases
TEST_CASES = [
    SourceTestCase(
        question="Ποια βήματα πρέπει να ακολουθήσει ο ιατρός στη νέα εφαρμογή Ηλεκτρονικής Συνταγογράφησης για να ξεκινήσει την αναζήτηση ενός ασθενή με HIV;",
        expected_source="Αναζήτηση HIV Ασθενή",
        language="GR"
    ),
    SourceTestCase(
        question="Ποια διαδικασία πρέπει να ακολουθήσει ο ιατρός στο Σύστημα Ηλεκτρονικής Συνταγογράφησης (ΣΗΣ) για να εκτελέσει ένα παραπεμπτικό;",
        expected_source="Εκτέλεση Παραπεμπτικών",
        language="GR"
    ),
    # Add more test cases here
]

@pytest.mark.parametrize("test_case", TEST_CASES)
def test_source_verification(test_case: SourceTestCase):
    """Test that the expected source is present in the response sources"""
    response = get_api_response(test_case)
    
    if not response:
        pytest.fail("No response received from API")
    
    sources = response.get('sources', [])
    if not sources:
        pytest.fail("No sources found in response")
    
    if not verify_sources(sources, test_case.expected_source):
        error_msg = (
            f"Expected source '{test_case.expected_source}' not found in any breadcrumb.\n"
            f"Available breadcrumbs:\n{format_sources_for_error(sources)}"
        )
        pytest.fail(error_msg) 