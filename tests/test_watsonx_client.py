import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from watsonx_client import WatsonxClient


class WatsonxClientDemoResponseTests(unittest.TestCase):
    def test_eggrolls_query_returns_recipe_response(self):
        client = WatsonxClient()
        response = client._demo_response("what is recipe of eggrolls", "")
        self.assertIn("Egg Rolls", response)
        self.assertIn("recipe", response.lower())


if __name__ == "__main__":
    unittest.main()
