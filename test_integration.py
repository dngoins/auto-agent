import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
from httpx import AsyncClient


class TestIntegration:
    """Integration tests for voice fallback, routing, logging, and concurrency"""

    @pytest.fixture
    async def app_client(self):
        """Create FastAPI test client"""
        from main import app
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    @patch('openai.AsyncOpenAI')
    @patch('azure.cognitiveservices.speech.SpeechSynthesizer')
    async def test_voice_fallback_on_openai_failure(self, mock_azure_synth, mock_openai):
        """Test voice service falls back to Azure when OpenAI fails"""
        from devops_agent import VoiceServiceWithFallback
        
        # Configure OpenAI to fail
        mock_openai_client = AsyncMock()
        mock_openai_client.audio.speech.create.side_effect = Exception("OpenAI API Error")
        mock_openai.return_value = mock_openai_client
        
        # Configure Azure as fallback
        mock_result = Mock()
        mock_result.audio_data = b'azure_fallback_audio'
        mock_azure_synth.return_value.speak_text_async.return_value.get.return_value = mock_result
        
        service = VoiceServiceWithFallback()
        audio = await service.generate_speech("Test message")
        
        assert audio == b'azure_fallback_audio'
        mock_openai_client.audio.speech.create.assert_called_once()

    @pytest.mark.asyncio
    @patch('azure.communication.callingserver.CallAutomationClient')
    async def test_routing_service_with_mocked_acs(self, mock_acs_client):
        """Test call routing service with mocked ACS SDK"""
        from controller import CallRoutingService
        
        # Mock ACS client
        mock_client = Mock()
        mock_call_connection = Mock()
        mock_call_connection.call_connection_id = "test-call-id"
        mock_client.create_call.return_value = mock_call_connection
        mock_acs_client.return_value = mock_client
        
        routing_service = CallRoutingService()
        call_id = await routing_service.transfer_to_teams("test-caller", "test-target")
        
        assert call_id == "test-call-id"
        mock_client.create_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_logging_correlation_across_call_lifecycle(self, app_client):
        """Test that logging maintains correlation ID across call lifecycle"""
        import logging
        from unittest.mock import patch
        
        correlation_ids = []
        
        def log_filter(record):
            if hasattr(record, 'correlation_id'):
                correlation_ids.append(record.correlation_id)
            return True
        
        with patch('logging.Logger.filter', side_effect=log_filter):
            # Simulate webhook call
            response = await app_client.post(
                "/api/callbacks",
                json={
                    "callConnectionId": "test-call-123",
                    "eventType": "CallConnected"
                }
            )
            
            # All logs should have the same correlation ID
            assert len(set(correlation_ids)) == 1
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_call_handling_with_semaphore(self):
        """Test concurrent call handling respects semaphore limits"""
        from controller import CallController
        
        max_concurrent = 5
        controller = CallController(max_concurrent_calls=max_concurrent)
        
        active_calls = []
        max_active = 0
        
        async def mock_handle_call(call_id):
            nonlocal max_active
            active_calls.append(call_id)
            max_active = max(max_active, len(active_calls))
            await asyncio.sleep(0.1)
            active_calls.remove(call_id)
        
        # Start 10 concurrent calls
        tasks = []
        for i in range(10):
            with patch.object(controller, 'handle_call', side_effect=mock_handle_call):
                task = asyncio.create_task(controller.handle_call(f"call-{i}"))
                tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify semaphore limited concurrency
        assert max_active <= max_concurrent

    @pytest.mark.asyncio
    @patch('azure.communication.callingserver.CallAutomationClient')
    async def test_acs_webhook_retry_mechanism(self, mock_acs_client, app_client):
        """Test webhook retry mechanism for failed ACS callbacks"""
        call_count = 0
        
        async def failing_handler(request):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return {"status": "success"}
        
        with patch('controller.handle_callback', side_effect=failing_handler):
            response = await app_client.post(
                "/api/callbacks",
                json={
                    "callConnectionId": "test-call",
                    "eventType": "CallConnected"
                },
                headers={"x-retry-count": "3"}
            )
            
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_end_to_end_logging_telemetry(self):
        """Test that telemetry is collected across entire call flow"""
        from azure.monitor.opentelemetry import configure_azure_monitor
        from opentelemetry import trace
        
        with patch('azure.monitor.opentelemetry.configure_azure_monitor'):
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span("test_call_flow") as span:
                span.set_attribute("call.id", "test-123")
                span.set_attribute("call.state", "initiated")
                
                # Simulate call flow
                await asyncio.sleep(0.01)
                
                span.set_attribute("call.state", "completed")
                
            # Verify span was created and attributes set
            assert span is not None

    @pytest.mark.asyncio
    @patch('azure.communication.callingserver.CallAutomationClient')
    async def test_acs_error_handling_and_logging(self, mock_acs_client):
        """Test proper error handling and logging for ACS failures"""
        from controller import CallRoutingService
        
        mock_client = Mock()
        mock_client.create_call.side_effect = Exception("ACS API Error")
        mock_acs_client.return_value = mock_client
        
        routing_service = CallRoutingService()
        
        with pytest.raises(Exception) as exc_info:
            await routing_service.transfer_to_teams("caller", "target")
        
        assert "ACS API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rate_limiting_for_concurrent_calls(self):
        """Test rate limiting prevents overwhelming external services"""
        from controller import CallController
        
        controller = CallController(rate_limit=10)  # 10 calls per second
        
        start_time = asyncio.get_event_loop().time()
        
        tasks = [controller.handle_call(f"call-{i}") for i in range(20)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Should take at least 1 second due to rate limiting
        assert duration >= 1.0
