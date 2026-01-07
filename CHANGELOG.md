# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-07

### Added

- Complete manual sensor configuration documentation for Home Assistant
- Detailed MQTT configuration examples in README

### Changed

- **STABLE RELEASE**: First production-ready version
- Complete and accurate documentation aligned with implementation
- All features tested and working: MQTT publishing, MQTT Discovery, OCR, VNC connection

### Fixed

- All documentation now accurately reflects the MQTT-based implementation
- README includes both MQTT Discovery and manual configuration options

## [0.3.1] - 2026-01-07

### Changed
- Documentation updated to accurately reflect MQTT-based implementation
- README.md now correctly describes all MQTT configuration options
- Improved configuration documentation with detailed option descriptions

### Note
- This is the current stable implementation using MQTT for sensor communication
- MQTT Discovery support for automatic sensor registration
- Configurable MQTT broker, topics, and credentials

## [0.3.0] - 2026-01-03

### Fixed
- **CRITICAL**: Fixed regex pattern syntax error causing "nothing to repeat at position 5"
  - Properly escaped pipe characters in patterns: `(.*)\|*./h`
  - OCR patterns now work correctly
- Updated MQTT Client API to VERSION2 (removed deprecation warning)

### Added
- Comprehensive debug logging for troubleshooting
  - VNC connection status logging
  - Screenshot capture details (coordinates, file size)
  - OCR processing information (image size, raw output length)
  - Full stack traces on errors
- Screenshots now saved with timestamps for better debugging
- Fullscreen capture immediately after VNC login
- DEBUGGING.md with step-by-step troubleshooting guide

### Changed
- Debug screenshots now always saved when `debug_screenshots: true` (not just on errors)
- Screenshots include timestamp in filename for history tracking

## [0.2.0] - 2026-01-03

### Added
- MQTT Discovery support for automatic sensor registration in Home Assistant
- Configurable VNC connect delay (`vnc_connect_delay`)
- Configurable Tesseract OCR settings (`tesseract_config`)
- Configurable MQTT Discovery prefix and node ID
- Enhanced translations (de/en) for all configuration options
- Comprehensive README with all features documented

### Changed
- **CRITICAL FIX**: Corrected OCR regex patterns to match working original script
  - Changed `throughput_pattern` from `(.*)\|*\.?/h` to `(.*)\|*./h`
  - Changed `volume_pattern` from `(.*)\|*\.` to `(.*)\|*.`
  - Simplified OCR text parsing (less aggressive cleaning)
- Improved error handling and retry logic
- Updated Python dependencies to current versions

### Fixed
- OCR pattern matching now correctly interprets display output
- VNC connection stability improvements
- Debug screenshot functionality

## [0.1.0] - Initial Release

### Added
- Basic VNC connection to BWT Perla device
- OCR-based value extraction (throughput & volume)
- MQTT publishing of sensor values
- Multi-architecture support (aarch64, armv7, amd64)
- Home Assistant Add-on structure
- Configurable parameters via Add-on UI
- Debug mode with screenshot capture
- Signal handling for graceful shutdown
