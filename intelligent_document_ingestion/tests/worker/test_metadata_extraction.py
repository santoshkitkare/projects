from worker import extract_metadata
from unittest.mock import patch

@patch("worker.call_llm", return_value={"name": "John Doe", "email": "john@doe.com"})
def test_extract_metadata(mock_llm):
    meta = extract_metadata("dummy text")
    assert meta["name"] == "John Doe"
