"""
Timer command detection.

This module provides functionality to identify and process timer-related
commands in transcribed text, including starting, pausing, stopping, and
resetting timers.
"""

import logging
import re
import time
from typing import Dict, Any, List, Optional, Pattern, Match, Tuple, Callable

from ..core.interfaces import TimerManagerInterface, CommandDetectorInterface
from ..models.timer import TimerCommand
from ..services.event_bus import EventBus, EventType

logger = logging.getLogger(__name__)


class TimerCommandDetector(CommandDetectorInterface):
    """Detects and processes timer-related commands in transcribed text."""
    
    def __init__(self, timer_manager: Optional[TimerManagerInterface] = None):
        """Initialize the timer command detector.
        
        Args:
            timer_manager: Timer manager for handling commands
        """
        self.timer_manager = timer_manager
        self.event_bus = EventBus()
        
        # Command patterns and handlers
        self.command_patterns: Dict[str, Tuple[Pattern, Callable[[Dict[str, Any]], None]]] = {}
        
        # Register built-in commands
        self._register_built_in_commands()
    
    def detect_commands(self, text: str) -> List[Dict[str, Any]]:
        """Detect timer commands in transcript text.
        
        Args:
            text: Transcript text to analyze
            
        Returns:
            List of detected commands with parameters
        """
        if not text:
            return []
        
        detected_commands = []
        
        # Debug log to see what text is being processed
        logger.debug(f"Analyzing text for timer commands: {text}")
        
        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()
        
        # Check each registered command pattern
        for command_name, (pattern, handler) in self.command_patterns.items():
            matches = pattern.finditer(text_lower)
            
            for match in matches:
                try:
                    # Extract command data
                    command_data = self._extract_command_data(match, command_name)
                    
                    if command_data:
                        # Execute the command handler
                        handler(command_data)
                        
                        # Add to results
                        detected_commands.append(command_data)
                        
                        logger.info(f"Executed timer command: {command_name} - Text: {text}")
                        
                        # Publish command executed event
                        self.event_bus.publish_simple(
                            EventType.COMMAND_EXECUTED,
                            command_data,
                            "TimerCommandDetector"
                        )
                except Exception as e:
                    logger.error(f"Error executing timer command {command_name}: {e}")
                    
                    # Publish command failed event
                    self.event_bus.publish_simple(
                        EventType.COMMAND_FAILED,
                        {
                            "command": command_name,
                            "error": str(e),
                            "text": text
                        },
                        "TimerCommandDetector"
                    )
        
        return detected_commands
    
    def register_pattern(self, name: str, pattern: str, 
                       handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register a new command pattern.
        
        Args:
            name: Name of the command pattern
            pattern: Regex pattern for matching
            handler: Function to call when pattern matches
        """
        compiled_pattern = re.compile(pattern)
        self.command_patterns[name] = (compiled_pattern, handler)
        logger.debug(f"Registered timer command pattern: {name}")
    
    def _register_built_in_commands(self) -> None:
        """Register built-in timer command patterns."""
        if not self.timer_manager:
            logger.warning("Timer manager not provided, timer commands will not be functional.")
            return
            
        # Log all registered patterns for debugging
        logger.debug("Registering timer command patterns")

        # Create timer: "set a timer for X minutes/seconds" - more permissive pattern
        self.register_pattern(
            "create_timer",
            r'(?:set|start|create|make)(?:\s+(?:a|an|the))?\s*timer(?:\s+for)?\s+(\d+)\s+(?:minute|minutes|min|mins|second|seconds|sec|secs)',
            self._handle_create_timer
        )
        
        # Create named timer: "set a timer named X for Y minutes/seconds" - more permissive
        self.register_pattern(
            "create_named_timer",
            r'(?:set|start|create|make)(?:\s+(?:a|an|the))?\s*timer\s+(?:called|named)\s+([\w\s]+?)(?:\s+for)?\s+(\d+)\s+(?:minute|minutes|min|mins|second|seconds|sec|secs)',
            self._handle_create_named_timer
        )
        
        # Pause timer: "pause timer" or "pause the timer named X" - more permissive
        self.register_pattern(
            "pause_timer",
            r'(?:pause|hold)(?:\s+(?:the|my|this))?\s*timer(?:\s+(?:called|named)\s+([\w\s]+))?',
            self._handle_pause_timer
        )
        
        # Resume timer: "resume timer" or "resume the timer named X" - more permissive
        self.register_pattern(
            "resume_timer",
            r'(?:resume|continue|unpause)(?:\s+(?:the|my|this))?\s*timer(?:\s+(?:called|named)\s+([\w\s]+))?',
            self._handle_resume_timer
        )
        
        # Stop/cancel timer: "stop timer" or "cancel the timer named X" - more permissive
        self.register_pattern(
            "stop_timer",
            r'(?:stop|cancel|end|terminate)(?:\s+(?:the|my|this))?\s*timer(?:\s+(?:called|named)\s+([\w\s]+))?',
            self._handle_stop_timer
        )
        
        # Reset timer: "reset timer" or "reset the timer named X" - more permissive
        self.register_pattern(
            "reset_timer",
            r'(?:reset|restart)(?:\s+(?:the|my|this))?\s*timer(?:\s+(?:called|named)\s+([\w\s]+))?',
            self._handle_reset_timer
        )
        
        # Log all registered patterns
        for name, (pattern, _) in self.command_patterns.items():
            logger.debug(f"Registered timer pattern '{name}': {pattern.pattern}")
    
    def _extract_command_data(self, match: Match, command_name: str) -> Dict[str, Any]:
        """Extract command data from a regex match.
        
        Args:
            match: Regex match object
            command_name: Name of the matched command
            
        Returns:
            Command data dictionary
        """
        result = {
            "command": command_name,
            "matched_text": match.group(0),
            "groups": [g for g in match.groups() if g is not None],
            "detected_at": time.time()
        }
        
        # Add specific data based on command type
        if command_name == "create_timer":
            result["duration"] = int(match.group(1))
            result["unit"] = match.group(2)
            result["timer_action"] = "create"
        
        elif command_name == "create_named_timer":
            result["name"] = match.group(1).strip()
            result["duration"] = int(match.group(2))
            result["unit"] = match.group(3)
            result["timer_action"] = "create"
        
        elif command_name in ["pause_timer", "resume_timer", "stop_timer", "reset_timer"]:
            # Extract timer name if specified, otherwise None
            timer_name = match.group(1).strip() if match.group(1) else None
            result["name"] = timer_name
            
            # Extract action type from command name
            action_map = {
                "pause_timer": "pause",
                "resume_timer": "resume",
                "stop_timer": "stop",
                "reset_timer": "reset"
            }
            result["timer_action"] = action_map.get(command_name)
        
        return result
    
    def _handle_create_timer(self, command_data: Dict[str, Any]) -> None:
        """Handle a basic timer creation command.
        
        Args:
            command_data: Command data dictionary
        """
        if not self.timer_manager:
            return
            
        duration = command_data["duration"]
        unit = command_data["unit"]
        
        # Convert to seconds
        if unit.startswith('minute') or unit.startswith('min'):
            duration_seconds = duration * 60
        else:
            duration_seconds = duration
        
        # Set the timer
        timer_name = f"Timer_{int(time.time())}"
        self.timer_manager.set_timer(timer_name, duration_seconds)
        
        logger.info(f"Created timer for {duration} {unit}")
    
    def _handle_create_named_timer(self, command_data: Dict[str, Any]) -> None:
        """Handle a named timer creation command.
        
        Args:
            command_data: Command data dictionary
        """
        if not self.timer_manager:
            return
            
        name = command_data["name"]
        duration = command_data["duration"]
        unit = command_data["unit"]
        
        # Convert to seconds
        if unit.startswith('minute') or unit.startswith('min'):
            duration_seconds = duration * 60
        else:
            duration_seconds = duration
        
        # Set the timer
        self.timer_manager.set_timer(name, duration_seconds)
        
        logger.info(f"Created timer '{name}' for {duration} {unit}")
    
    def _handle_pause_timer(self, command_data: Dict[str, Any]) -> None:
        """Handle a timer pause command.
        
        Args:
            command_data: Command data dictionary
        """
        if not self.timer_manager:
            return
            
        name = command_data.get("name")
        
        # If a specific timer was named
        if name:
            self._pause_specific_timer(name)
        else:
            self._pause_most_recent_timer()
    
    def _pause_specific_timer(self, timer_name: str) -> None:
        """Pause a specific timer by name.
        
        Args:
            timer_name: Name of the timer to pause
        """
        timers = self.timer_manager.get_timers()
        if timer_name in timers:
            timer = timers[timer_name]
            if hasattr(timer, 'pause') and callable(timer.pause):
                timer.pause()
                logger.info(f"Paused timer '{timer_name}'")
                
                # Publish timer event
                self.event_bus.publish_simple(
                    EventType.TIMER_CANCELLED,  # Using CANCELLED since there's no PAUSED event
                    {"timer_name": timer_name, "action": "pause"},
                    "TimerCommandDetector"
                )
            else:
                logger.error(f"Timer '{timer_name}' doesn't support pause")
        else:
            logger.warning(f"Timer '{timer_name}' not found")
    
    def _pause_most_recent_timer(self) -> None:
        """Pause the most recently created active timer."""
        timers = self.timer_manager.get_timers()
        active_timers = [(name, timer) for name, timer in timers.items() 
                        if getattr(timer, 'status', None) == 'ACTIVE']
        
        if active_timers:
            # Sort by creation time (newest first)
            sorted_timers = sorted(active_timers, key=lambda x: x[1].created_at, reverse=True)
            newest_timer_name, newest_timer = sorted_timers[0]
            
            if hasattr(newest_timer, 'pause') and callable(newest_timer.pause):
                newest_timer.pause()
                logger.info(f"Paused most recent timer '{newest_timer_name}'")
                
                # Publish timer event
                self.event_bus.publish_simple(
                    EventType.TIMER_CANCELLED,  # Using CANCELLED since there's no PAUSED event
                    {"timer_name": newest_timer_name, "action": "pause"},
                    "TimerCommandDetector"
                )
            else:
                logger.error(f"Timer '{newest_timer_name}' doesn't support pause")
        else:
            logger.warning("No active timers to pause")
    
    def _handle_resume_timer(self, command_data: Dict[str, Any]) -> None:
        """Handle a timer resume command.
        
        Args:
            command_data: Command data dictionary
        """
        if not self.timer_manager:
            return
            
        name = command_data.get("name")
        
        # If a specific timer was named
        if name:
            self._resume_specific_timer(name)
        else:
            self._resume_most_recent_timer()
    
    def _resume_specific_timer(self, timer_name: str) -> None:
        """Resume a specific timer by name.
        
        Args:
            timer_name: Name of the timer to resume
        """
        timers = self.timer_manager.get_timers()
        if timer_name in timers:
            timer = timers[timer_name]
            if hasattr(timer, 'resume') and callable(timer.resume):
                timer.resume()
                logger.info(f"Resumed timer '{timer_name}'")
                
                # Publish timer event
                self.event_bus.publish_simple(
                    EventType.TIMER_CREATED,  # Using CREATED since there's no RESUMED event
                    {"timer_name": timer_name, "action": "resume"},
                    "TimerCommandDetector"
                )
            else:
                logger.error(f"Timer '{timer_name}' doesn't support resume")
        else:
            logger.warning(f"Timer '{timer_name}' not found")
    
    def _resume_most_recent_timer(self) -> None:
        """Resume the most recently paused timer."""
        timers = self.timer_manager.get_timers()
        paused_timers = [(name, timer) for name, timer in timers.items() 
                        if getattr(timer, 'status', None) == 'PAUSED']
        
        if paused_timers:
            # Sort by creation time (newest first)
            sorted_timers = sorted(paused_timers, key=lambda x: x[1].created_at, reverse=True)
            newest_timer_name, newest_timer = sorted_timers[0]
            
            if hasattr(newest_timer, 'resume') and callable(newest_timer.resume):
                newest_timer.resume()
                logger.info(f"Resumed most recent timer '{newest_timer_name}'")
                
                # Publish timer event
                self.event_bus.publish_simple(
                    EventType.TIMER_CREATED,  # Using CREATED since there's no RESUMED event
                    {"timer_name": newest_timer_name, "action": "resume"},
                    "TimerCommandDetector"
                )
            else:
                logger.error(f"Timer '{newest_timer_name}' doesn't support resume")
        else:
            logger.warning("No paused timers to resume")
    
    def _handle_stop_timer(self, command_data: Dict[str, Any]) -> None:
        """Handle a timer stop/cancel command.
        
        Args:
            command_data: Command data dictionary
        """
        if not self.timer_manager:
            return
            
        name = command_data.get("name")
        
        # If a specific timer was named
        if name:
            success = self.timer_manager.cancel_timer(name)
            if success:
                logger.info(f"Stopped timer '{name}'")
            else:
                logger.warning(f"Timer '{name}' not found or already stopped")
        else:
            # Stop the most recent timer
            timers = self.timer_manager.get_timers()
            active_timers = [(name, timer) for name, timer in timers.items() 
                           if getattr(timer, 'status', None) == 'ACTIVE']
            
            if active_timers:
                # Sort by creation time (newest first)
                sorted_timers = sorted(active_timers, key=lambda x: x[1].created_at, reverse=True)
                newest_timer_name = sorted_timers[0][0]
                
                success = self.timer_manager.cancel_timer(newest_timer_name)
                if success:
                    logger.info(f"Stopped most recent timer '{newest_timer_name}'")
                else:
                    logger.warning(f"Failed to stop timer '{newest_timer_name}'")
            else:
                logger.warning("No active timers to stop")
    
    def _handle_reset_timer(self, command_data: Dict[str, Any]) -> None:
        """Handle a timer reset command.
        
        Args:
            command_data: Command data dictionary
        """
        if not self.timer_manager:
            return
            
        name = command_data.get("name")
        
        # If a specific timer was named
        if name:
            self._reset_specific_timer(name)
        else:
            self._reset_most_recent_timer()
    
    def _reset_specific_timer(self, timer_name: str) -> None:
        """Reset a specific timer by name.
        
        Args:
            timer_name: Name of the timer to reset
        """
        timers = self.timer_manager.get_timers()
        if timer_name in timers:
            timer = timers[timer_name]
            
            # Get timer details before cancelling
            duration = timer.duration
            
            # Cancel the existing timer
            self.timer_manager.cancel_timer(timer_name)
            
            # Create a new timer with the same name and duration
            self.timer_manager.set_timer(timer_name, duration)
            
            logger.info(f"Reset timer '{timer_name}' with duration {duration} seconds")
        else:
            logger.warning(f"Timer '{timer_name}' not found")
    
    def _reset_most_recent_timer(self) -> None:
        """Reset the most recently created timer."""
        timers = self.timer_manager.get_timers()
        if not timers:
            logger.warning("No timers to reset")
            return
            
        # Sort by creation time (newest first)
        sorted_timer_items = sorted(timers.items(), 
                                  key=lambda x: x[1].created_at, 
                                  reverse=True)
        
        newest_timer_name, newest_timer = sorted_timer_items[0]
        
        # Get timer details before cancelling
        duration = newest_timer.duration
        
        # Cancel the existing timer
        self.timer_manager.cancel_timer(newest_timer_name)
        
        # Create a new timer with the same name and duration
        self.timer_manager.set_timer(newest_timer_name, duration)
        
        logger.info(f"Reset most recent timer '{newest_timer_name}' with duration {duration} seconds")
