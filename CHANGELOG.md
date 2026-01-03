# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
