# Code Combiner

A powerful, high-performance utility for combining multiple code files into a single document with intelligent organization and formatting.

Perfect for AI analysis, code reviews, documentation, and creating comprehensive code archives.

## Features

### 🚀 Performance Optimized
- **Lazy Loading**: Instantly loads large directories by loading folders on-demand
- **Parallel Processing**: Utilizes multi-core CPUs for 8x faster file processing
- **Smart Caching**: Icon and directory caching for lightning-fast UI
- **Extension-based Detection**: Quick file type heuristics instead of expensive content analysis

### 📁 Intelligent File Selection
- **Hierarchical Tree View**: Navigate your project structure intuitively
- **Lazy Folder Expansion**: Only scans folders when you expand them
- **File Type Filtering**: Checkbox-based extension filtering
- **Reverse Ignore Mode**: Include-only or exclude mode for flexible selection
- **Smart Folder Selection**: Check/uncheck entire folders at once

### 🛠️ Advanced Features
- **Multiple Output Formats**: Simple, Detailed, or Markdown with syntax highlighting
- **Virtual Environment Management**: Automatically creates and manages Python 3.10.11+ venv
- **Comprehensive Logging**: Performance metrics and debug logs in `./logs/`
- **Recent Projects**: Quick access to frequently used directories
- **Auto-save Settings**: Remembers your preferences

### 📊 Performance Monitoring
- Detailed performance logs for every operation
- Automatic bottleneck detection (operations >100ms flagged)
- CPU core detection and utilization
- GPU detection (for future enhancements)

## Installation

### Requirements
- Python 3.10.11 or higher (3.14.0 recommended)
- Windows, macOS, or Linux

### Quick Start

1. Clone the repository:
```bash
git clone https://github.com/FatStinkyPanda/code-combiner.git
cd code-combiner
```

2. Run the application:
```bash
python code_combiner_2_0.py
```

That's it! The application will:
- Check your Python version
- Create a virtual environment (`.venv_codecombiner`)
- Install PyQt6 if needed
- Launch the GUI

## Usage

### Basic Workflow

1. **Select Folder**: Click "Browse..." or use File → Open Folder
2. **Wait for Instant Load**: Root directory loads in <0.1 seconds
3. **Expand & Filter**: Expand folders to explore, uncheck extensions/files to exclude
4. **Combine Files**: Click "Combine Files" to process
5. **View Output**: Preview or save the combined file

### Reverse Ignore Mode

Enable "Reverse Ignore Mode" to:
- Start with everything **unchecked** (ignored)
- Check only the files/folders you want to **include**
- Perfect for large projects where you only need specific files

### File Type Filtering

- Automatically discovers extensions as you expand folders
- Check/uncheck extension checkboxes to filter globally
- Filters apply immediately without re-scanning

### Output Formats

**Simple**: Basic separators with file paths
```
================================================================================
FILE: src/main.py
================================================================================
```

**Detailed**: Includes file metadata
```
================================================================================
FILE: src/main.py
SIZE: 1024 bytes
MODIFIED: 2025-01-13 19:30:00
================================================================================
```

**Markdown**: Syntax-highlighted code blocks
```markdown
## src/main.py

```python
# Your code here
```
```

## Performance

### Tested Performance Metrics

**Directory Loading**:
- Small projects (<100 files): <0.05s
- Medium projects (100-1000 files): 0.1-0.3s
- Large projects (1000-10000 files): 0.3-1.0s
- Very large projects (10000+ files): 1.0-3.0s

**File Processing** (with parallel mode):
- Sequential: ~1 file/second
- Parallel (8 cores): ~8 files/second
- Parallel (20 cores): ~15-20 files/second

**System Requirements**:
- Minimal: 2GB RAM, dual-core CPU
- Recommended: 4GB+ RAM, quad-core+ CPU for parallel processing

## Architecture

### Core Components

- **FileTreeWidget**: Lazy-loading hierarchical tree with smart caching
- **FileProcessorWorker**: Multi-threaded file processor with parallel I/O
- **AnimatedStatusBar**: Smooth status animations with fade effects
- **Performance Logger**: Comprehensive timing and error tracking

### Key Optimizations

1. **Icon Caching**: Pre-loads UI icons once, reuses for all items
2. **Extension Heuristics**: Fast file type detection without content reading
3. **Lazy Directory Loading**: Only scans when user expands folders
4. **Parallel File Reading**: ThreadPoolExecutor for concurrent I/O
5. **Smart State Management**: Tracks loaded directories to avoid re-scanning

## Logging

Performance and debug logs are saved to `./logs/`:

- `codecombiner_YYYYMMDD_HHMMSS.log`: Main application log
- `performance_YYYYMMDD_HHMMSS.log`: Detailed performance metrics

### Finding Bottlenecks

```bash
# Find slow operations
grep "SLOW:" logs/performance_*.log

# Sort operations by time
grep "Elapsed:" logs/performance_*.log | sort -k5 -nr
```

## Development

### Project Structure

```
CodeCombiner/
├── code_combiner_2_0.py      # Main application
├── .gitignore                 # Git ignore rules
├── README.md                  # This file
├── .venv_codecombiner/        # Virtual environment (auto-created)
└── logs/                      # Performance & debug logs (auto-created)
```

### Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with appropriate logging
4. Test performance impact
5. Submit a pull request

## License

Copyright © 2025 Daniel A Bissey

Permission is hereby granted to use this software for personal and commercial purposes.

## Author

**Daniel A Bissey**
Email: support@fatstinkypanda.com
GitHub: [@FatStinkyPanda](https://github.com/FatStinkyPanda)

## Changelog

### Version 2.0 (2025-01-13)

**Major Features**:
- Complete rewrite with lazy loading architecture
- Parallel file processing with multi-core support
- Comprehensive performance logging and monitoring
- Virtual environment automation
- Icon caching and performance optimizations
- Reverse ignore mode for include-only workflows
- Dynamic extension filtering

**Performance Improvements**:
- 50-100x faster directory loading
- 8x faster file processing (with 8+ cores)
- Reduced memory usage for large projects
- Eliminated UI freezing during operations

**Bug Fixes**:
- Fixed RecursionError in AnimatedStatusBar
- Fixed PyQt6 signal parameter mismatches
- Fixed initialization order issues
- Added proper error handling and logging

### Version 1.0

- Initial release
- Basic file combining functionality
- Simple tree view
- Multiple output formats

## Acknowledgments

Built with:
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - Modern Python GUI framework
- [Python](https://www.python.org/) - The language that powers it all

---

**Perfect for AI analysis, code reviews, and documentation.**

*Designed, Created, and Developed by Daniel A Bissey*
