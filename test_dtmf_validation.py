import pytest
from unittest.mock import Mock, AsyncMock, patch


class TestDTMFValidation:
    """Test DTMF input validation logic"""

    def test_valid_single_digit(self):
        """Test validation of single digit DTMF input"""
        from contracts import DTMFInput
        valid_inputs = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        for digit in valid_inputs:
            dtmf = DTMFInput(tone=digit)
            assert dtmf.tone == digit

    def test_valid_star_pound(self):
        """Test validation of * and # DTMF inputs"""
        from contracts import DTMFInput
        dtmf_star = DTMFInput(tone='*')
        dtmf_pound = DTMFInput(tone='#')
        assert dtmf_star.tone == '*'
        assert dtmf_pound.tone == '#'

    def test_invalid_dtmf_input(self):
        """Test rejection of invalid DTMF inputs"""
        from contracts import DTMFInput
        invalid_inputs = ['A', 'B', 'C', 'D', 'a', 'abc', '', ' ', '10']
        for invalid in invalid_inputs:
            with pytest.raises(ValueError):
                DTMFInput(tone=invalid)

    def test_dtmf_input_trimming(self):
        """Test that DTMF input is properly trimmed"""
        from contracts import DTMFInput
        dtmf = DTMFInput(tone=' 5 ')
        assert dtmf.tone == '5'

    def test_dtmf_sequence_validation(self):
        """Test validation of DTMF sequences"""
        from contracts import DTMFSequence
        valid_sequence = DTMFSequence(tones=['1', '2', '3'])
        assert len(valid_sequence.tones) == 3
        assert valid_sequence.tones == ['1', '2', '3']

    def test_empty_dtmf_sequence(self):
        """Test handling of empty DTMF sequence"""
        from contracts import DTMFSequence
        with pytest.raises(ValueError):
            DTMFSequence(tones=[])

    def test_dtmf_timeout_validation(self):
        """Test DTMF timeout configuration"""
        from contracts import DTMFConfig
        config = DTMFConfig(timeout_seconds=30)
        assert config.timeout_seconds == 30
        
        with pytest.raises(ValueError):
            DTMFConfig(timeout_seconds=-1)
        
        with pytest.raises(ValueError):
            DTMFConfig(timeout_seconds=0)
