from pages.Login import login_user
from unittest.mock import patch

@patch("requests.post")
def test_login_api(mock_post):
    mock_post.return_value.json.return_value = {"access_token": "xyz"}
    token = login_user("admin", "admin@123")
    assert token == "xyz"
