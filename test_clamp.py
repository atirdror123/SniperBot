
import unittest
from ai_signal_engine import AISignalEngine

class TestClamping(unittest.TestCase):
    def test_clamping(self):
        engine = AISignalEngine()
        
        # Test 1: Direct function verification (if accessible, otherwise mock)
        # Since _call_gemini is internal and makes web requests, we can't easily unit test it 
        # without mocking requests.post. 
        # However, we can test the score_stock public method if we mock _call_gemini or requests.
        pass

if __name__ == "__main__":
    # Quick dirty test: Inject a fake response into requests.post using unittest.mock
    from unittest.mock import patch, MagicMock
    import json

    print("TESTING SCORE CLAMPING...")
    
    with patch('requests.post') as mock_post:
        # Mock response with score 250 (Hallucination)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{
                        'text': '```json\n{ "score": 250, "reason": "Super bullish!" }\n```'
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response

        engine = AISignalEngine()
        # force _call_gemini to be called
        score, reason = engine._call_gemini("test prompt")
        
        print(f"Raw Input: 250")
        print(f"Output Score: {score}")
        
        if score > 100:
            print("❌ FAILURE: Score not clamped!")
        elif score == 100:
            print("✅ SUCCESS: Score clamped to 100.")
        else:
            print(f"❓ UNEXPECTED: {score}")

