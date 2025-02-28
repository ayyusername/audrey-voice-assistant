# Changelog

All notable changes to Project Audrey will be documented in this file.

## [2.7.0] - 2025-02-27

### Added
- Added timer UI display in the control panel to visualize active timers
- Implemented real-time timer countdown display with progress bars
- Added visual indication of timer status (active/paused)
- Improved logging of timer creation and completion events

### Fixed
- Fixed session error in transcript saving functionality
- Fixed timer command detection with more permissive pattern matching
- Improved logging for better debugging of command detection
- Fixed service container registration bug with string interface keys 
- Added comprehensive debug logging for command detection process
- Made timer command detection more robust with broader recognition patterns

## [2.6.8] - 2025-02-27

### Added
- Added specialized timer command detector for better recognition of timer control commands
- Added functionality to identify start, pause, stop, and reset timer commands in transcripts
- Implemented detection of timer commands with or without specific timer names
- Added comprehensive unit tests for the timer command detection functionality

### Fixed
- Fixed duplicate initialization issues in transcription service
- Improved command detection with multiple command detectors working in parallel
- Enhanced service container registration for command detectors