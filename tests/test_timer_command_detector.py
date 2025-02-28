"""
Tests for the timer command detector module.

This module tests the functionality of the timer command detector, ensuring
that it correctly identifies timer commands in transcribed text.
"""

import time
import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from audrey.core.timer_command_detector import TimerCommandDetector
from audrey.models.timer import Timer, TimerStatus


class TestTimerCommandDetector(unittest.TestCase):
    """Tests for the TimerCommandDetector class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a mock timer manager
        self.timer_manager = MagicMock()
        
        # Create the timer command detector with the mock timer manager
        self.detector = TimerCommandDetector(self.timer_manager)
        
        # Mock the event bus publish method
        self.event_bus_patch = patch("audrey.core.timer_command_detector.EventBus")
        self.mock_event_bus = self.event_bus_patch.start()
        
        # Set up mock timer for get_timers
        self.mock_timer = MagicMock(spec=Timer)
        self.mock_timer.duration = 60
        self.mock_timer.created_at = time.time()
        self.mock_timer.status = TimerStatus.ACTIVE
        
        # Setup timer_manager.get_timers to return our mock timer
        self.timer_manager.get_timers.return_value = {"test_timer": self.mock_timer}
    
    def tearDown(self):
        """Clean up after each test."""
        self.event_bus_patch.stop()
    
    def test_create_timer(self):
        """Test creating a basic timer."""
        # Test text
        text = "set a timer for 5 minutes"
        
        # Detect commands
        commands = self.detector.detect_commands(text)
        
        # Check results
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "create_timer")
        self.assertEqual(commands[0]["duration"], 5)
        self.assertEqual(commands[0]["unit"], "minutes")
        
        # Verify timer manager was called
        self.timer_manager.set_timer.assert_called_once()
        
        # Check the duration conversion (5 minutes = 300 seconds)
        _, duration = self.timer_manager.set_timer.call_args[0]
        self.assertEqual(duration, 300)
    
    def test_create_named_timer(self):
        """Test creating a named timer."""
        # Test text
        text = "create a timer named pasta for 10 minutes"
        
        # Detect commands
        commands = self.detector.detect_commands(text)
        
        # Check results
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "create_named_timer")
        self.assertEqual(commands[0]["name"], "pasta")
        self.assertEqual(commands[0]["duration"], 10)
        self.assertEqual(commands[0]["unit"], "minutes")
        
        # Verify timer manager was called with correct arguments
        self.timer_manager.set_timer.assert_called_once_with("pasta", 600)
    
    def test_pause_timer(self):
        """Test pausing a timer."""
        # Test text
        text = "pause the timer"
        
        # Detect commands
        commands = self.detector.detect_commands(text)
        
        # Check results
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "pause_timer")
        
        # Verify mock timer's pause method was called
        self.mock_timer.pause.assert_called_once()
    
    def test_pause_specific_timer(self):
        """Test pausing a specific timer."""
        # Test text
        text = "pause the timer named pasta"
        
        # Detect commands
        commands = self.detector.detect_commands(text)
        
        # Check results
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "pause_timer")
        self.assertEqual(commands[0]["name"], "pasta")
    
    def test_resume_timer(self):
        """Test resuming a timer."""
        # Setup mock timer with PAUSED status
        self.mock_timer.status = TimerStatus.PAUSED
        
        # Test text
        text = "resume the timer"
        
        # Detect commands
        commands = self.detector.detect_commands(text)
        
        # Check results
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "resume_timer")
        
        # Verify mock timer's resume method was called
        self.mock_timer.resume.assert_called_once()
    
    def test_stop_timer(self):
        """Test stopping a timer."""
        # Test text
        text = "stop the timer"
        
        # Setup cancel_timer to return True (success)
        self.timer_manager.cancel_timer.return_value = True
        
        # Detect commands
        commands = self.detector.detect_commands(text)
        
        # Check results
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "stop_timer")
        
        # Verify timer manager's cancel_timer was called
        self.timer_manager.cancel_timer.assert_called_once()
    
    def test_stop_specific_timer(self):
        """Test stopping a specific timer."""
        # Test text
        text = "cancel the timer named pasta"
        
        # Setup cancel_timer to return True (success)
        self.timer_manager.cancel_timer.return_value = True
        
        # Detect commands
        commands = self.detector.detect_commands(text)
        
        # Check results
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "stop_timer")
        self.assertEqual(commands[0]["name"], "pasta")
        
        # Verify timer manager's cancel_timer was called with correct name
        self.timer_manager.cancel_timer.assert_called_once_with("pasta")
    
    def test_reset_timer(self):
        """Test resetting a timer."""
        # Test text
        text = "reset the timer"
        
        # Setup cancel_timer to return True (success)
        self.timer_manager.cancel_timer.return_value = True
        
        # Detect commands
        commands = self.detector.detect_commands(text)
        
        # Check results
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "reset_timer")
        
        # Verify cancel_timer and set_timer were both called
        self.timer_manager.cancel_timer.assert_called_once()
        self.assertEqual(self.timer_manager.set_timer.call_count, 1)
    
    def test_multiple_commands(self):
        """Test detecting multiple commands in a single transcript."""
        # Test text with multiple commands
        text = "set a timer for 3 minutes and then pause the timer named pasta"
        
        # Detect commands
        commands = self.detector.detect_commands(text)
        
        # Should detect two separate commands
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0]["command"], "create_timer")
        self.assertEqual(commands[1]["command"], "pause_timer")

if __name__ == "__main__":
    unittest.main()
