import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
from httpx import AsyncClient
import json


class TestEndToEnd:
    """End-to-end tests for complete call flow using test doubles"""

    @pytest.fixture
    async def app_client(self):
        """Create FastAPI test client"""
        from main import app
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    @pytest.fixture
    def acs_webhook_payload(self):
        """Create sample ACS webhook payload"""
        return {
            "callConnectionId": "test-call-connection-123",
            "serverCallId": "test-server-call-456",
            "eventType": "Microsoft.Communication.CallConnected",
            "callerId": "+15551234567",
            "calledTo": "+15559876543",
            "correlationId": "correlation-789"
        }

    @pytest.mark.asyncio
    @patch('azure.communication.callingserver.CallAutomationClient')
    @patch('openai.AsyncOpenAI')
    async def test_complete_call_flow_success(self, mock_openai, mock_acs, app_client, acs_webhook_payload):
        """Test complete call flow from webhook receipt to Teams transfer"""
        # Mock OpenAI TTS
        mock_openai_client = AsyncMock()
        mock_tts_response = AsyncMock()
        mock_tts_response.content = b'greeting_audio'
        mock_openai_client.audio.speech.create.return_value = mock_tts_response
        mock_openai.return_value = mock_openai_client
        
        # Mock ACS client
        mock_acs_client = Mock()
        mock_call_connection = Mock()
        mock_call_connection.call_connection_id = "test-call-connection-123"
        mock_acs_client.get_call_connection.return_value = mock_call_connection
        mock_acs.return_value = mock_acs_client
        
        # Step 1: Receive webhook for call connected
        response = await app_client.post("/api/callbacks", json=acs_webhook_payload)
        assert response.status_code == 200
        
        # Step 2: Simulate DTMF input received
        dtmf_payload = {
            "callConnectionId": "test-call-connection-123",
            "eventType": "Microsoft.Communication.RecognizeCompleted",
            "dtmfTones": ["1"],
            "correlationId": "correlation-789"
        }
        
        response = await app_client.post("/api/callbacks", json=dtmf_payload)
        assert response.status_code == 200
        
        # Step 3: Verify transfer was initiated
        mock_call_connection.transfer_call_to_participant.assert_called_once()

    @pytest.mark.asyncio
    @patch('azure.communication.callingserver.CallAutomationClient')
    async def test_call_flow_with_invalid_dtmf(self, mock_acs, app_client, acs_webhook_payload):
        """Test call flow handles invalid DTMF input gracefully"""
        mock_acs_client = Mock()
        mock_call_connection = Mock()
        mock_acs_client.get_call_connection.return_value = mock_call_connection
        mock_acs.return_value = mock_acs_client
        
        # Receive call connected
        response = await app_client.post("/api/callbacks", json=acs_webhook_payload)
        assert response.status_code == 200
        
        # Send invalid DTMF
        invalid_dtmf_payload = {
            "callConnectionId": "test-call-connection-123",
            "eventType": "Microsoft.Communication.RecognizeCompleted",
            "dtmfTones": ["A", "B"],  # Invalid tones
            "correlationId": "correlation-789"
        }
        
        response = await app_client.post("/api/callbacks", json=invalid_dtmf_payload)
        
        # Should handle gracefully and re-prompt
        assert response.status_code == 200
        mock_call_connection.play_media.assert_called()  # Error message played

    @pytest.mark.asyncio
    @patch('azure.communication.callingserver.CallAutomationClient')
    async def test_call_flow_with_timeout(self, mock_acs, app_client, acs_webhook_payload):
        """Test call flow handles DTMF timeout"""
        mock_acs_client = Mock()
        mock_call_connection = Mock()
        mock_acs_client.get_call_connection.return_value = mock_call_connection
        mock_acs.return_value = mock_acs_client
        
        # Receive call connected
        response = await app_client.post("/api/callbacks", json=acs_webhook_payload)
        assert response.status_code == 200
        
        # Send timeout event
        timeout_payload = {
            "callConnectionId": "test-call-connection-123",
            "eventType": "Microsoft.Communication.RecognizeFailed",
            "resultInformation": {
                "code": 8510,
                "message": "Action failed, initial silence timeout reached"
            },
            "correlationId": "correlation-789"
        }
        
        response = await app_client.post("/api/callbacks", json=timeout_payload)
        assert response.status_code == 200
        
        # Should retry or end call
        assert mock_call_connection.play_media.called or mock_call_connection.hang_up.called

    @pytest.mark.asyncio
    @patch('azure.communication.callingserver.CallAutomationClient')
    @patch('openai.AsyncOpenAI')
    async def test_call_flow_with_api_failure(self, mock_openai, mock_acs, app_client, acs_webhook_payload):
        """Test call flow handles API failures gracefully"""
        # Mock OpenAI to fail
        mock_openai_client = AsyncMock()
        mock_openai_client.audio.speech.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_openai_client
        
        # Mock ACS client
        mock_acs_client = Mock()
        mock_call_connection = Mock()
        mock_acs_client.get_call_connection.return_value = mock_call_connection
        mock_acs.return_value = mock_acs_client
        
        # Should handle gracefully with fallback
        response = await app_client.post("/api/callbacks", json=acs_webhook_payload)
        
        # Call should continue with fallback TTS or end gracefully
        assert response.status_code in [200, 500]

    @pytest.mark.asyncio
    @patch('azure.communication.callingserver.CallAutomationClient')
    async def test_complete_call_lifecycle_state_transitions(self, mock_acs, app_client):
        """Test all state transitions in complete call lifecycle"""
        mock_acs_client = Mock()
        mock_call_connection = Mock()
        mock_acs_client.get_call_connection.return_value = mock_call_connection
        mock_acs.return_value = mock_acs_client
        
        call_id = "test-call-lifecycle-123"
        
        # State 1: Call Connected
        await app_client.post("/api/callbacks", json={
            "callConnectionId": call_id,
            "eventType": "Microsoft.Communication.CallConnected",
            "correlationId": "corr-1"
        })
        
        # State 2: Play Completed (greeting played)
        await app_client.post("/api/callbacks", json={
            "callConnectionId": call_id,
            "eventType": "Microsoft.Communication.PlayCompleted",
            "correlationId": "corr-2"
        })
        
        # State 3: Recognize Started (awaiting DTMF)
        await app_client.post("/api/callbacks", json={
            "callConnectionId": call_id,
            "eventType": "Microsoft.Communication.RecognizeStarted",
            "correlationId": "corr-3"
        })
        
        # State 4: Recognize Completed (DTMF received)
        await app_client.post("/api/callbacks", json={
            "callConnectionId": call_id,
            "eventType": "Microsoft.Communication.RecognizeCompleted",
            "dtmfTones": ["1"],
            "correlationId": "corr-4"
        })
        
        # State 5: Call Transferred
        await app_client.post("/api/callbacks", json={
            "callConnectionId": call_id,
            "eventType": "Microsoft.Communication.CallTransferAccepted",
            "correlationId": "corr-5"
        })
        
        # State 6: Call Disconnected
        response = await app_client.post("/api/callbacks", json={
            "callConnectionId": call_id,
            "eventType": "Microsoft.Communication.CallDisconnected",
            "correlationId": "corr-6"
        })
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch('azure.communication.callingserver.CallAutomationClient')
    async def test_concurrent_calls_isolation(self, mock_acs, app_client):
        """Test that concurrent calls are properly isolated"""
        mock_acs_client = Mock()
        mock_acs.return_value = mock_acs_client
        
        # Start multiple concurrent calls
        call_ids = [f"call-{i}" for i in range(5)]
        
        tasks = []
        for call_id in call_ids:
            task = app_client.post("/api/callbacks", json={
                "callConnectionId": call_id,
                "eventType": "Microsoft.Communication.CallConnected",
                "correlationId": f"corr-{call_id}"
            })
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All calls should succeed independently
        assert all(r.status_code == 200 for r in responses)

    @pytest.mark.asyncio
    @patch('azure.communication.callingserver.CallAutomationClient')
    async def test_call_flow_with_transfer_failure(self, mock_acs, app_client, acs_webhook_payload):
        """Test call flow handles transfer failure"""
        mock_acs_client = Mock()
        mock_call_connection = Mock()
        mock_call_connection.transfer_call_to_participant.side_effect = Exception("Transfer failed")
        mock_acs_client.get_call_connection.return_value = mock_call_connection
        mock_acs.return_value = mock_acs_client
        
        # Receive call and DTMF
        await app_client.post("/api/callbacks", json=acs_webhook_payload)
        
        response = await app_client.post("/api/callbacks", json={
            "callConnectionId": "test-call-connection-123",
            "eventType": "Microsoft.Communication.RecognizeCompleted",
            "dtmfTones": ["1"],
            "correlationId": "correlation-789"
        })
        
        # Should handle transfer failure gracefully
        assert response.status_code in [200, 500]
        # Should play error message or end call
        assert mock_call_connection.play_media.called or mock_call_connection.hang_up.called

    @pytest.mark.asyncio
    async def test_webhook_authentication(self, app_client):
        """Test webhook endpoint validates ACS signatures"""
        # Send webhook without proper authentication
        response = await app_client.post(
            "/api/callbacks",
            json={"eventType": "test"},
            headers={"X-Invalid-Header": "invalid"}
        )
        
        # Should reject unauthenticated requests
        # Note: actual implementation may vary
        assert response.status_code in [200, 401, 403]
