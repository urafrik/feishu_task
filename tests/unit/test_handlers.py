import pytest
from app.handlers import create_event_handler # This is what we test now
from unittest.mock import MagicMock, AsyncMock

# Remove unused imports that were causing errors
# from app.handlers import _extract_github_info, _parse_task_command

# Mock dependencies
@pytest.fixture
def mock_feishu_client():
    return AsyncMock()

@pytest.fixture
def mock_bitable_client():
    return AsyncMock()

@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.feishu.encrypt_key = "test_encrypt_key"
    settings.feishu.verification_token = "test_verification_token"
    return settings

def test_create_event_handler(mock_feishu_client, mock_bitable_client, mock_settings):
    """
    Test that the event handler is created without errors.
    """
    handler = create_event_handler(mock_feishu_client, mock_bitable_client, mock_settings)
    assert handler is not None
    # We can add more specific assertions here if needed, 
    # e.g., checking if the correct event handlers are registered. 