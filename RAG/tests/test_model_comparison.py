import json
import pytest
import requests
import pandas as pd
from typing import Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the absolute path of the test file's directory
TEST_DIR = Path(__file__).parent.absolute()
DATA_DIR = TEST_DIR / "data"
EXCEL_PATH = DATA_DIR / "Doctor_AIAgent_tests.xlsx"

# Configuration
SHEET_NAME = "AutomatedModelComparison"
MODEL = "cohere.command-r-08-2024" # Make sure to restart the app after changing the config file
OUTPUT_COLUMN = "Command R"
ROW_LIMIT = 0  # Limit to first n rows - 0 to run all rows

OUTPUT_PATH = DATA_DIR / f"{OUTPUT_COLUMN.replace(' ', '_')}_responses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
logger.info(f"Output file will be created at: {OUTPUT_PATH}")

# Global variable to store responses
responses = []

@dataclass
class ModelTestCase:
    """Represents a test case for model comparison"""
    question: str
    model: str
    output_column: str

def read_test_cases(excel_path: Path, sheet_name: str, model: str, output_column: str, limit: int = None) -> List[ModelTestCase]:
    """Read test cases from Excel file"""
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, engine='openpyxl')
        logger.info(f"Successfully read {len(df)} rows from Excel file")
    except Exception as e:
        raise ValueError(f"Error reading Excel sheet '{sheet_name}': {str(e)}")
    
    test_cases = []
    row_count = 0
    
    for _, row in df.iterrows():
        if pd.isna(row['Question']):  # Skip empty rows
            continue
            
        test_cases.append(ModelTestCase(
            question=row['Question'],
            model=model,
            output_column=output_column
        ))
        
        row_count += 1
        if limit and row_count >= limit:
            logger.info(f"Limited to first {limit} rows")
            break
    
    logger.info(f"Created {len(test_cases)} test cases")
    return test_cases

def get_model_response(test_case: ModelTestCase) -> str:
    """Get response from model and concatenate content chunks"""
    url = "http://localhost:9000/ask"
    headers = {"Content-Type": "application/json"}
    data = {
        "message": test_case.question,
        "genModel": test_case.model,
        "language": "GR",
        "conversation": []
    }
    
    response = requests.post(url, headers=headers, json=data, stream=True)
    content_chunks = []
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data:'):
                try:
                    chunk = json.loads(line[5:])  # Remove 'data:' prefix
                    if chunk.get('type') == 'content':
                        content_chunks.append(chunk.get('content', ''))
                except json.JSONDecodeError:
                    continue
    
    return ''.join(content_chunks)

def create_output_excel(test_cases: List[ModelTestCase], responses: List[str], output_path: Path):
    """Create a new Excel file with questions and responses"""
    logger.info(f"Creating output Excel file with {len(responses)} responses")
    df = pd.DataFrame({
        'Question': [tc.question for tc in test_cases],
        OUTPUT_COLUMN: responses
    })
    
    df.to_excel(output_path, index=False)
    logger.info(f"Successfully created output file: {output_path}")

# Read test cases
test_cases = read_test_cases(EXCEL_PATH, SHEET_NAME, MODEL, OUTPUT_COLUMN, limit=ROW_LIMIT)

@pytest.fixture(scope="session", autouse=True)
def create_excel_file():
    """Fixture to create Excel file after all tests are complete"""
    yield
    if responses:  # Only create file if we have responses
        create_output_excel(test_cases, responses, OUTPUT_PATH)
    else:
        logger.info("No responses collected, skipping file creation")

@pytest.mark.parametrize("test_case", test_cases)
def test_model_responses(test_case: ModelTestCase):
    """Test model response for a single question"""
    logger.info(f"Processing question: {test_case.question}")
    response = get_model_response(test_case)
    responses.append(response)
    logger.info(f"Got response of length: {len(response)}")
    assert response.strip(), f"Empty response received for question: {test_case.question}" 