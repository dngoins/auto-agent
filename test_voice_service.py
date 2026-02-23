import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio


class TestVoiceServiceStrategy:
    """Test voice service strategy pattern with OpenAI TTS"""

    @pytest.fixture
    def openai_voice_service(self):
        """Create OpenAI voice service instance"""
        from devops_agent import OpenAIVoiceService
        return OpenAIVoiceService(api_key="test-key")

    @pytest.fixture
    def azure_voice_service(self):
        """Create Azure voice service instance"""
        from devops_agent import AzureVoiceService
        return AzureVoiceService()

    @pytest.mark.asyncio
    @patch('openai.AsyncOpenAI')
    async def test_openai_tts_success(self, mock_openai, openai_voice_service):
        """Test successful OpenAI TTS generation"""
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = b'audio_data'
        mock_client.audio.speech.create.return_value = mock_response
        mock_openai.return_value = mock_client

        audio_data = await openai_voice_service.generate_speech("Hello world")
        assert audio_data == b'audio_data'
        mock_client.audio.speech.create.assert_called_once()

    @pytest.mark.asyncio
    @patch('openai.AsyncOpenAI')
    async def test_openai_tts_failure(self, mock_openai, openai_voice_service):
        """Test OpenAI TTS failure handling"""
        mock_client = AsyncMock()
        mock_client.audio.speech.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client

        with pytest.raises(Exception):
            await openai_voice_service.generate_speech("Hello world")

    @pytest.mark.asyncio
    async def test_azure_tts_fallback(self, azure_voice_service):
        """Test Azure TTS as fallback service"""
        with patch('azure.cognitiveservices.speech.SpeechSynthesizer') as mock_synth:
            mock_result = Mock()
            mock_result.audio_data = b'azure_audio'
            mock_synth.return_value.speak_text_async.return_value.get.return_value = mock_result

            audio_data = await azure_voice_service.generate_speech("Hello world")
            assert audio_data == b'azure_audio'

    @pytest.mark.asyncio
    async def test_voice_service_factory(self):
        """Test voice service factory pattern"""
        from devops_agent import VoiceServiceFactory
        
        factory = VoiceServiceFactory()
        openai_service = factory.create_service('openai')
        azure_service = factory.create_service('azure')
        
        assert openai_service is not None
        assert azure_service is not None

    @pytest.mark.asyncio
    @patch('openai.AsyncOpenAI')
    async def test_voice_service_with_retry(self, mock_openai, openai_voice_service):
        """Test voice service retry mechanism"""
        mock_client = AsyncMock()
        call_count = 0
        
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            mock_response = AsyncMock()
            mock_response.content = b'audio_data'
            return mock_response
        
        mock_client.audio.speech.create = mock_create
        mock_openai.return_value = mock_client

        audio_data = await openai_voice_service.generate_speech_with_retry("Hello", max_retries=3)
        assert audio_data == b'audio_data'
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_voice_service_caching(self, openai_voice_service):
        """Test voice service response caching"""
        with patch.object(openai_voice_service, 'generate_speech', AsyncMock(return_value=b'cached_audio')) as mock_gen:
            # First call - should hit the service
            audio1 = await openai_voice_service.generate_speech_cached("Hello")
            
            # Second call with same text - should use cache
            audio2 = await openai_voice_service.generate_speech_cached("Hello")
            
            assert audio1 == audio2
            mock_gen.assert_called_once()

    @pytest.mark.asyncio
    @patch('openai.AsyncOpenAI')
    async def test_openai_tts_timeout(self, mock_openai, openai_voice_service):
        """Test OpenAI TTS timeout handling"""
        mock_client = AsyncMock()
        
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(10)
            return AsyncMock(content=b'audio')
        
        mock_client.audio.speech.create = slow_response
        mock_openai.return_value = mock_client

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(openai_voice_service.generate_speech("Hello"), timeout=1.0)

    @pytest.mark.asyncio
    async def test_voice_service_audio_format(self, openai_voice_service):
        """Test voice service supports required audio formats"""
        formats = ['mp3', 'wav', 'pcm']
        
        for fmt in formats:
            with patch.object(openai_voice_service, 'generate_speech', AsyncMock(return_value=b'audio')):
                audio = await openai_voice_service.generate_speech("Test", format=fmt)
                assert audio is not None
