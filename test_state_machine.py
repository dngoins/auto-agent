import pytest
from unittest.mock import Mock, AsyncMock, patch
from enum import Enum


class CallState(Enum):
    """Mock call states for testing"""
    INITIATED = "initiated"
    GREETING = "greeting"
    AWAITING_DTMF = "awaiting_dtmf"
    PROCESSING_DTMF = "processing_dtmf"
    TRANSFERRING = "transferring"
    TRANSFERRED = "transferred"
    ENDED = "ended"
    ERROR = "error"


class TestStateMachine:
    """Test state machine transitions for call flow"""

    @pytest.fixture
    def state_machine(self):
        """Create a mock state machine instance"""
        from controller import CallStateMachine
        return CallStateMachine()

    def test_initial_state(self, state_machine):
        """Test that state machine starts in INITIATED state"""
        assert state_machine.current_state == CallState.INITIATED

    @pytest.mark.asyncio
    async def test_transition_initiated_to_greeting(self, state_machine):
        """Test transition from INITIATED to GREETING"""
        await state_machine.transition_to(CallState.GREETING)
        assert state_machine.current_state == CallState.GREETING

    @pytest.mark.asyncio
    async def test_transition_greeting_to_awaiting_dtmf(self, state_machine):
        """Test transition from GREETING to AWAITING_DTMF"""
        await state_machine.transition_to(CallState.GREETING)
        await state_machine.transition_to(CallState.AWAITING_DTMF)
        assert state_machine.current_state == CallState.AWAITING_DTMF

    @pytest.mark.asyncio
    async def test_transition_awaiting_to_processing_dtmf(self, state_machine):
        """Test transition when DTMF input is received"""
        await state_machine.transition_to(CallState.GREETING)
        await state_machine.transition_to(CallState.AWAITING_DTMF)
        await state_machine.transition_to(CallState.PROCESSING_DTMF)
        assert state_machine.current_state == CallState.PROCESSING_DTMF

    @pytest.mark.asyncio
    async def test_transition_processing_to_transferring(self, state_machine):
        """Test transition from PROCESSING_DTMF to TRANSFERRING"""
        await state_machine.transition_to(CallState.GREETING)
        await state_machine.transition_to(CallState.AWAITING_DTMF)
        await state_machine.transition_to(CallState.PROCESSING_DTMF)
        await state_machine.transition_to(CallState.TRANSFERRING)
        assert state_machine.current_state == CallState.TRANSFERRING

    @pytest.mark.asyncio
    async def test_transition_transferring_to_transferred(self, state_machine):
        """Test successful transfer completion"""
        await state_machine.transition_to(CallState.GREETING)
        await state_machine.transition_to(CallState.AWAITING_DTMF)
        await state_machine.transition_to(CallState.PROCESSING_DTMF)
        await state_machine.transition_to(CallState.TRANSFERRING)
        await state_machine.transition_to(CallState.TRANSFERRED)
        assert state_machine.current_state == CallState.TRANSFERRED

    @pytest.mark.asyncio
    async def test_transition_to_error_state(self, state_machine):
        """Test transition to ERROR state from any state"""
        await state_machine.transition_to(CallState.GREETING)
        await state_machine.transition_to(CallState.ERROR)
        assert state_machine.current_state == CallState.ERROR

    @pytest.mark.asyncio
    async def test_invalid_state_transition(self, state_machine):
        """Test that invalid transitions are rejected"""
        with pytest.raises(ValueError):
            await state_machine.transition_to(CallState.TRANSFERRED)

    @pytest.mark.asyncio
    async def test_state_transition_callbacks(self, state_machine):
        """Test that state transition callbacks are invoked"""
        callback_invoked = False
        
        def on_transition(from_state, to_state):
            nonlocal callback_invoked
            callback_invoked = True
            assert from_state == CallState.INITIATED
            assert to_state == CallState.GREETING
        
        state_machine.register_callback(on_transition)
        await state_machine.transition_to(CallState.GREETING)
        assert callback_invoked

    def test_state_history_tracking(self, state_machine):
        """Test that state machine tracks state history"""
        assert len(state_machine.history) == 1
        assert state_machine.history[0] == CallState.INITIATED

    @pytest.mark.asyncio
    async def test_state_rollback(self, state_machine):
        """Test rollback to previous state on error"""
        await state_machine.transition_to(CallState.GREETING)
        await state_machine.transition_to(CallState.AWAITING_DTMF)
        
        with pytest.raises(Exception):
            await state_machine.transition_to_with_rollback(CallState.PROCESSING_DTMF, should_fail=True)
        
        assert state_machine.current_state == CallState.AWAITING_DTMF
