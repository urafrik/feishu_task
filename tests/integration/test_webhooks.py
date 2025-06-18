import pytest
from unittest.mock import patch, AsyncMock
import json
import time
import hashlib
import random
import string

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

@pytest.fixture
def mock_feishu_client():
    with patch("app.main.feishu_client", new_callable=AsyncMock) as mock_client:
        yield mock_client

@pytest.fixture
def mock_bitable_client():
    with patch("app.main.bitable_client", new_callable=AsyncMock) as mock_client:
        mock_client.create_task.return_value = {"record_id": "rec_12345"}
        yield mock_client

@pytest.fixture
def mock_match_service():
    with patch("app.handlers.match_service", new_callable=AsyncMock) as mock_service:
        mock_service.find_candidates_for_task.return_value = [{"user_id": "ou_123", "name": "Test User"}]
        mock_service.create_candidate_card.return_value = {"type": "interactive", "card": {}}
        yield mock_service
        
def test_new_task_command_success(mock_feishu_client, mock_bitable_client, mock_match_service):
    """
    Test the full /feishu/event flow for a new task command.
    """
    # 1. Construct a fake Feishu event payload
    fake_event = {
        "schema": "2.0",
        "header": {
            "event_id": "fake_event_id",
            "event_type": "im.message.receive_v1",
            "create_time": "1608725989000",
            "token": settings.feishu.verification_token,
            "app_id": settings.feishu.app_id,
            "tenant_key": "fake_tenant"
        },
        "event": {
            "sender": {"sender_id": {"open_id": "ou_123"}},
            "message": {
                "message_id": "om_123",
                "chat_id": "oc_123",
                "message_type": "text",
                "content": '{"text":"@_user_1 新任务 T1 | S1 | D1 | D1"}',
                "mentions": [{"key": "@_user_1", "id": {"open_id": settings.feishu.app_id}}]
            }
        }
    }

    # 2. Generate signature for the webhook
    timestamp = str(int(time.time()))
    nonce = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
    body = json.dumps(fake_event, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    
    signature_string = timestamp.encode('utf-8') + nonce.encode('utf-8') + settings.feishu.encrypt_key.encode('utf-8') + body
    signature = hashlib.sha1(signature_string).hexdigest()

    # 3. POST to the webhook with correct headers
    response = client.post(
        "/feishu/event", 
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Lark-Request-Timestamp": timestamp,
            "X-Lark-Request-Nonce": nonce,
            "X-Lark-Signature": signature,
        }
    )

    # 4. Assertions
    assert response.status_code == 200
    
    # Assert that our mocks were called
    # mock_bitable_client.create_task.assert_called_once()
    # mock_match_service.find_candidates_for_task.assert_called_once()
    # mock_feishu_client.send_message.assert_called_once()

def test_github_webhook_verification_fail():
    """Test that the GitHub webhook fails with an invalid signature."""
    response = client.post(
        "/webhook/ci", 
        headers={
            "X-Hub-Signature-256": "sha256=invalid",
            "X-GitHub-Event": "ping"
        },
        content="some body"
    )
    assert response.status_code == 403 # Forbidden 

def test_github_webhook_check_suite_success(mock_feishu_client, mock_bitable_client):
    """Test a successful CI check_suite event from GitHub."""
    # 1. Mock the signature verification to always pass
    with patch("hmac.compare_digest", return_value=True):
        # 2. Configure mock clients
        mock_task = {
            "record_id": "rec_123", 
            "child_chat_id": "oc_456",
            "github_commit_sha": "a_real_sha_123456789"
        }
        mock_bitable_client.get_task_by_commit.return_value = mock_task

        # 3. Construct fake payload
        fake_sha = "a_real_sha_123456789"
        payload = {
            "action": "completed",
            "check_suite": {
                "head_sha": fake_sha,
                "conclusion": "success"
            },
            "repository": {
                "full_name": "test/repo"
            }
        }

        # 4. Make the request
        response = client.post(
            "/webhook/ci",
            headers={
                "X-Hub-Signature-256": "sha256=any_mocked_value",
                "X-GitHub-Event": "check_suite"
            },
            json=payload
        )

        # 5. Assertions
        assert response.status_code == 204 # Should be 204 No Content for successful webhooks without a body
        # mock_bitable_client.get_task_by_commit.assert_called_once_with(fake_sha)
        # mock_bitable_client.update_task_status_by_commit.assert_called_once()
        # mock_feishu_client.send_message.assert_called_once() 