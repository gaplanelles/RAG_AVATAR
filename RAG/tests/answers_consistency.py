import os
import json
import asyncio
import aiohttp
import time
from pathlib import Path
from typing import List, Dict
import difflib
from datetime import datetime

class AnswerConsistencyTest:
    def __init__(self, n_calls: int = 10):
        self.n_calls = n_calls
        self.base_url = "http://localhost:9000"
        self.answers_dir = Path("answers")
        self.answers_dir.mkdir(exist_ok=True)
        self.responses: List[Dict] = []

    async def fetch_response(self, session: aiohttp.ClientSession) -> Dict:
        """Make a single call to the /ask endpoint and collect the streaming response."""
        url = f"{self.base_url}/ask"
        payload = {
            "message": "πως αναζητω ασθενη;",
            "genModel": "cohere.command-r-plus-08-2024",
            "language": "GR",
            "conversation_id": "6ae1a86f-06b5-4efc-81e4-b40dc7a6c3a8",
            "conversation": [
                {
                    "role": "Assistant",
                    "content": "Καλώς ήρθατε! Μπορώ να σας βοηθήσω με ερωτήσεις που αφορούν αποκλειστικά στην χρήση της εφαρμογής και βρίσκονται μέσα στον Οδηγό Χρήσης της (manual). π.χ.Ποιά είναι τα βήματα για τη δημιουργία νέας επίσκεψης; Σύντομα θα μπορώ να σας βοηθήσω και σε περισσότερα θέματα καθώς οι γνώσεις μου εμπλουτίζονται συνέχεια. Πώς μπορώ να σας βοηθήσω σήμερα;"
                }
            ]
        }

        full_response = ""
        sources = None

        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"HTTP error: {response.status}")

                # Read the response in chunks
                async for chunk in response.content.iter_chunked(8192):  # 8KB chunks
                    if chunk:
                        try:
                            lines = chunk.decode('utf-8').split('\n')
                            for line in lines:
                                line = line.strip()
                                if line.startswith('data: '):
                                    try:
                                        data = json.loads(line[6:])
                                        if data['type'] == 'content':
                                            full_response += data['content']
                                        elif data['type'] == 'done':
                                            sources = data.get('sources', None)
                                    except json.JSONDecodeError as e:
                                        print(f"Error decoding JSON: {e}")
                                        continue
                        except UnicodeDecodeError as e:
                            print(f"Error decoding chunk: {e}")
                            continue

        except Exception as e:
            print(f"Error in fetch_response: {e}")
            return {
                "content": f"Error: {str(e)}",
                "sources": None,
                "timestamp": datetime.now().isoformat(),
                "error": True
            }

        return {
            "content": full_response,
            "sources": sources,
            "timestamp": datetime.now().isoformat(),
            "error": False
        }

    async def run_test(self):
        """Run the test by making multiple calls to the endpoint."""
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_response(session) for _ in range(self.n_calls)]
            self.responses = await asyncio.gather(*tasks)

    def save_responses(self):
        """Save all responses to individual files in the answers directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for i, response in enumerate(self.responses):
            filename = self.answers_dir / f"response_{timestamp}_{i+1}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(response, f, ensure_ascii=False, indent=2)

    def compare_responses(self) -> Dict:
        """Compare all responses and return a report of differences."""
        if not self.responses:
            return {"error": "No responses to compare"}

        # Filter out error responses
        valid_responses = [r for r in self.responses if not r.get("error", False)]
        if not valid_responses:
            return {"error": "No valid responses to compare"}

        report = {
            "total_calls": self.n_calls,
            "successful_calls": len(valid_responses),
            "failed_calls": len(self.responses) - len(valid_responses),
            "unique_responses": len(set(r["content"] for r in valid_responses)),
            "differences": []
        }

        # Compare each response with every other response
        for i in range(len(valid_responses)):
            for j in range(i + 1, len(valid_responses)):
                resp1 = valid_responses[i]
                resp2 = valid_responses[j]
                
                if resp1["content"] != resp2["content"]:
                    diff = list(difflib.unified_diff(
                        resp1["content"].splitlines(),
                        resp2["content"].splitlines(),
                        lineterm=''
                    ))
                    report["differences"].append({
                        "response_pair": (i+1, j+1),
                        "diff": diff
                    })

        return report

async def main():
    test = AnswerConsistencyTest(n_calls=10)
    print("Starting consistency test...")
    await test.run_test()
    print("Saving responses...")
    test.save_responses()
    print("Comparing responses...")
    report = test.compare_responses()
    
    print("\nTest Results:")
    print(f"Total calls made: {report['total_calls']}")
    print(f"Successful calls: {report['successful_calls']}")
    print(f"Failed calls: {report['failed_calls']}")
    print(f"Number of unique responses: {report['unique_responses']}")
    print(f"Number of different response pairs: {len(report['differences'])}")
    
    if report['differences']:
        print("\nDifferences found between responses:")
        for diff in report['differences']:
            print(f"\nDifferences between responses {diff['response_pair'][0]} and {diff['response_pair'][1]}:")
            print('\n'.join(diff['diff']))

if __name__ == "__main__":
    asyncio.run(main())
