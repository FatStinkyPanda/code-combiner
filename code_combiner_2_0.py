import os
import sys
import threading
import mimetypes
import time
import logging
import traceback
import subprocess
import venv
from pathlib import Path
from datetime import datetime
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing

# ============================================================================
# PYTHON VERSION AND VIRTUAL ENVIRONMENT SETUP
# ============================================================================
REQUIRED_PYTHON_VERSION = (3, 10, 11)
VENV_DIR = Path(__file__).parent / ".venv_codecombiner"

def check_python_version():
    """Check if running Python 3.10.11 or compatible."""
    current_version = sys.version_info[:3]
    if current_version < REQUIRED_PYTHON_VERSION:
        print(f"⚠ Warning: Python {'.'.join(map(str, REQUIRED_PYTHON_VERSION))} recommended, running {'.'.join(map(str, current_version))}")
        print("Consider upgrading Python for optimal performance.")
    else:
        print(f"✓ Python version {'.'.join(map(str, current_version))} is compatible")

def setup_virtual_environment():
    """Create and activate virtual environment if not already running in one."""
    # Check if already in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

    if in_venv:
        print(f"✓ Running in virtual environment: {sys.prefix}")
        return True

    # Check if venv directory exists
    if not VENV_DIR.exists():
        print(f"Creating virtual environment at {VENV_DIR}...")
        try:
            venv.create(VENV_DIR, with_pip=True)
            print("✓ Virtual environment created successfully")
        except Exception as e:
            print(f"⚠ Warning: Could not create virtual environment: {e}")
            print("Continuing without virtual environment...")
            return False
    else:
        print(f"✓ Virtual environment found at {VENV_DIR}")

    # Determine the python executable in the venv
    if sys.platform == "win32":
        venv_python = VENV_DIR / "Scripts" / "python.exe"
    else:
        venv_python = VENV_DIR / "bin" / "python"

    # If not in venv, restart script with venv python
    if not in_venv and venv_python.exists():
        print(f"Restarting in virtual environment...")
        try:
            # Re-run this script with the venv Python
            result = subprocess.run([str(venv_python), __file__] + sys.argv[1:])
            sys.exit(result.returncode)
        except Exception as e:
            print(f"⚠ Warning: Could not restart in venv: {e}")
            print("Continuing with current Python...")
            return False

    return True

# ============================================================================
# PERFORMANCE LOGGING SETUP
# ============================================================================
# Configure comprehensive logging for performance tracking and debugging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Create formatters
detailed_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
simple_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Main logger
logger = logging.getLogger('CodeCombiner')
logger.setLevel(logging.DEBUG)

# File handler for detailed logs
file_handler = logging.FileHandler(LOG_DIR / f'codecombiner_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(detailed_formatter)
logger.addHandler(file_handler)

# Console handler for important messages
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(simple_formatter)
logger.addHandler(console_handler)

# Performance logger
perf_logger = logging.getLogger('CodeCombiner.Performance')
perf_logger.setLevel(logging.DEBUG)
perf_handler = logging.FileHandler(LOG_DIR / f'performance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
perf_handler.setFormatter(detailed_formatter)
perf_logger.addHandler(perf_handler)

def log_performance(func):
    """Decorator to log function execution time and errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get the function name for logging
        func_name = f"{func.__module__}.{func.__qualname__}"
        start_time = time.perf_counter()
        perf_logger.debug(f"ENTER: {func_name}")

        try:
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            perf_logger.debug(f"EXIT: {func_name} - Elapsed: {elapsed:.4f}s")

            # Log slow operations (>100ms)
            if elapsed > 0.1:
                perf_logger.warning(f"SLOW: {func_name} took {elapsed:.4f}s")

            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            perf_logger.error(f"ERROR in {func_name} after {elapsed:.4f}s: {str(e)}")
            perf_logger.error(traceback.format_exc())
            raise

    return wrapper

# Detect available processing capabilities
CPU_COUNT = multiprocessing.cpu_count()
logger.info(f"System has {CPU_COUNT} CPU cores available")

# Check for GPU (basic detection - PyQt doesn't typically use GPU)
try:
    import torch
    GPU_AVAILABLE = torch.cuda.is_available()
    if GPU_AVAILABLE:
        logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
    else:
        logger.info("No GPU detected or CUDA not available")
except ImportError:
    GPU_AVAILABLE = False
    logger.info("PyTorch not installed - GPU acceleration not available")

# ============================================================================
# AUTOMATIC DEPENDENCY INSTALLATION
# ============================================================================
# This section automatically checks for and installs required dependencies
# making this script completely standalone and portable.

@log_performance
def check_and_install_dependencies():
    """
    Check for required dependencies and install them if missing.
    This makes the script fully standalone.
    """
    logger.info("Checking dependencies...")
    required_packages = {
        'PyQt6': 'PyQt6'
    }

    missing_packages = []

    # Check which packages are missing
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"✓ {package_name} is already installed")
            logger.info(f"{package_name} is installed")
        except ImportError:
            print(f"✗ {package_name} is not installed")
            logger.warning(f"{package_name} is missing")
            missing_packages.append(package_name)

    # Install missing packages
    if missing_packages:
        print(f"\nInstalling missing dependencies: {', '.join(missing_packages)}")
        print("This may take a few moments...\n")
        logger.info(f"Installing packages: {missing_packages}")

        for package in missing_packages:
            try:
                print(f"Installing {package}...")
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", package],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                print(f"✓ {package} installed successfully")
                logger.info(f"{package} installed successfully")
            except subprocess.CalledProcessError as e:
                error_msg = f"Failed to install {package}: {e}"
                print(f"✗ {error_msg}")
                logger.error(error_msg)
                print("\nPlease install manually using:")
                print(f"  pip install {package}")
                sys.exit(1)

        print("\n✓ All dependencies installed successfully!")
        print("Continuing with application startup...\n")
        logger.info("All dependencies installed")
    else:
        print("✓ All dependencies are satisfied\n")
        logger.info("All dependencies satisfied")

# Run startup checks before importing PyQt6
if __name__ == "__main__":
    print("=" * 70)
    print("Code Combiner - Startup")
    print("=" * 70)

    # Check Python version
    check_python_version()

    # Setup virtual environment (will restart script if needed)
    setup_virtual_environment()

    # Check and install dependencies
    check_and_install_dependencies()
    print("=" * 70)
    print()

# ============================================================================
# MAIN APPLICATION IMPORTS
# ============================================================================

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTreeView, QTextEdit,
    QCheckBox, QProgressBar, QSplitter, QFrame, QTabWidget,
    QLineEdit, QGroupBox, QFormLayout, QMessageBox, QStyle,
    QStyledItemDelegate, QHeaderView, QSpinBox, QComboBox,
    QTreeWidget, QTreeWidgetItem, QDialog, QDialogButtonBox,
    QGraphicsOpacityEffect, QSizePolicy, QToolButton, QToolTip,
    QStatusBar, QScrollArea, QStyleFactory, QMenu
)
from PyQt6.QtCore import (
    Qt, QDir, QDirIterator, QThread, pyqtSignal, QSize,
    QStandardPaths, QModelIndex, QSettings, QObject, QTimer,
    QPropertyAnimation, QEasingCurve, QEvent, QRect, QPoint,
    QMimeData, QByteArray, QSortFilterProxyModel, QCoreApplication,
    QBuffer, QMargins, pyqtProperty
)
from PyQt6.QtGui import (
    QFont, QIcon, QColor, QPalette, QTextOption, QTextDocument,
    QSyntaxHighlighter, QTextCharFormat, QBrush, QAction, QPixmap,
    QPainter, QRadialGradient, QLinearGradient, QPen, QCursor,
    QTextCursor, QFontMetrics, QImage, QGuiApplication, QShortcut,
    QKeySequence, QTransform, QPainterPath, QTextFormat
)

# Initialize QApplication at the module level for global settings
app = QApplication(sys.argv)

# Application-wide stylesheet
APP_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #f5f5f7;
}

QSplitter::handle {
    background-color: #e0e0e0;
}

QGroupBox {
    border: 1px solid #c0c0c0;
    border-radius: 6px;
    margin-top: 12px;
    font-weight: bold;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 5px;
    background-color: #ffffff;
}

QTreeWidget {
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    background-color: #ffffff;
    alternate-background-color: #f9f9f9;
}

QTreeWidget::item {
    padding: 4px;
    border-bottom: 1px solid #f0f0f0;
}

QTreeWidget::item:selected {
    background-color: #e7f0fa;
    color: #000000;
}

QTextEdit {
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    background-color: #ffffff;
    selection-background-color: #b2d7ff;
    font-family: "Consolas", "Courier New", monospace;
}

QPushButton {
    background-color: #007aff;
    color: white;
    border-radius: 5px;
    padding: 8px 16px;
    font-weight: bold;
    border: none;
}

QPushButton:hover {
    background-color: #0069d9;
}

QPushButton:pressed {
    background-color: #0062cc;
}

QPushButton:disabled {
    background-color: #cccccc;
    color: #666666;
}

QLineEdit {
    padding: 6px;
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    background-color: #ffffff;
}

QProgressBar {
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    text-align: center;
    background-color: #ffffff;
    height: 20px;
}

QProgressBar::chunk {
    background-color: #007aff;
    border-radius: 3px;
}

QComboBox {
    padding: 6px;
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    background-color: #ffffff;
    min-width: 6em;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 20px;
    border-left: 1px solid #c0c0c0;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
}

QTabWidget::pane {
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    background-color: #ffffff;
    top: -1px;
}

QTabBar::tab {
    background-color: #f0f0f0;
    border: 1px solid #c0c0c0;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 8px 12px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    border-bottom: 1px solid #ffffff;
}

QTabBar::tab:hover:!selected {
    background-color: #e0e0e0;
}

QStatusBar {
    background-color: #f5f5f7;
    color: #333333;
}

QToolTip {
    background-color: #2a2a2a;
    color: #ffffff;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 4px;
}

QScrollBar:vertical {
    border: none;
    background-color: #f0f0f0;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #c0c0c0;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #a0a0a0;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background-color: #f0f0f0;
    height: 10px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #c0c0c0;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #a0a0a0;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #c0c0c0;
    border-radius: 4px;
}

QMenu::item {
    padding: 6px 25px 6px 25px;
}

QMenu::item:selected {
    background-color: #e7f0fa;
    color: #000000;
}

QLabel[title="true"] {
    font-size: 18pt;
    font-weight: bold;
    color: #333333;
}

QLabel[subtitle="true"] {
    font-size: 10pt;
    color: #666666;
}

"""


# Material Design-inspired color palette
class AppColors:
    PRIMARY = "#007aff"
    PRIMARY_DARK = "#0062cc"
    PRIMARY_LIGHT = "#e7f0fa"
    ACCENT = "#ff3b30"
    BACKGROUND = "#f5f5f7"
    SURFACE = "#ffffff"
    ERROR = "#ff3b30"
    SUCCESS = "#34c759"
    WARNING = "#ff9500"
    INFO = "#007aff"
    TEXT_PRIMARY = "#333333"
    TEXT_SECONDARY = "#666666"
    TEXT_DISABLED = "#9e9e9e"
    DIVIDER = "#e0e0e0"


# Syntax highlighter for code preview
class CodeSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self.highlighting_rules = []

        # Keyword format
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000FF"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "\\bdef\\b", "\\bclass\\b", "\\bimport\\b", "\\bfrom\\b", "\\breturn\\b",
            "\\bif\\b", "\\belif\\b", "\\belse\\b", "\\bfor\\b", "\\bwhile\\b",
            "\\btry\\b", "\\bexcept\\b", "\\bfinally\\b", "\\braise\\b", "\\bwith\\b",
            "\\bas\\b", "\\bpass\\b", "\\bcontinue\\b", "\\bbreak\\b", "\\byield\\b",
            "\\blambda\\b", "\\bglobal\\b", "\\bnonlocal\\b", "\\bassert\\b", "\\bdel\\b"
        ]

        for pattern in keywords:
            rule = (pattern, keyword_format)
            self.highlighting_rules.append(rule)

        # String format (single quotes)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#008000"))
        self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", string_format))

        # String format (double quotes)
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', string_format))

        # Comment format
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((r"#[^\n]*", comment_format))

        # Number format
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#FF8000"))
        self.highlighting_rules.append((r"\b[0-9]+\b", number_format))

        # Function format
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#800080"))
        function_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((r"\b[A-Za-z0-9_]+(?=\s*\()", function_format))

        # Class format
        class_format = QTextCharFormat()
        class_format.setForeground(QColor("#800000"))
        class_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((r"\bclass\s+[A-Za-z0-9_]+\b", class_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = pattern
            index = text.find(expression[0]) if isinstance(expression, str) else text.indexOf(expression)
            while index >= 0:
                length = len(expression) if isinstance(expression, str) else expression.matchedLength()
                self.setFormat(index, length, format)
                index = text.find(expression, index + length) if isinstance(expression, str) else text.indexOf(
                    expression, index + length)

        self.setCurrentBlockState(0)


# Determine if a file is a text file
def is_text_file(file_path):
    # Common text file extensions
    text_extensions = {
        '.py', '.txt', '.md', '.json', '.yaml', '.yml', '.csv',
        '.ini', '.cfg', '.conf', '.html', '.css', '.js', '.jsx',
        '.ts', '.tsx', '.env', '.gitignore', '.xml', '.sql',
        '.sh', '.bat', '.ps1', '.toml', '.rst', '.asciidoc',
        '.properties', '.gradle', '.swift', '.kt', '.kts',
        '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.php',
        '.rb', '.pl', '.go', '.rs', '.dart', '.lua', '.r'
    }

    # Try to determine MIME type
    mime_type, _ = mimetypes.guess_type(file_path)

    # Check if extension suggests text file
    ext = os.path.splitext(file_path)[1].lower()
    if ext in text_extensions:
        return True

    # Check if MIME type suggests text file
    if mime_type and mime_type.startswith(('text/', 'application/json', 'application/xml')):
        return True

    # Try to read file as text if not determined by extension or MIME
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sample = f.read(1024)
            # Check if sample contains mostly ASCII characters
            if all(ord(c) < 128 for c in sample if c not in '\r\n\t'):
                return True
            return False
    except:
        return False


# Loading overlay widget
class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Set up animation timer
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(40)  # Update every 40ms for smooth animation

        # Label for loading text
        self.text_label = QLabel(self)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setStyleSheet("""
            color: #333333;
            background-color: rgba(255, 255, 255, 220);
            border-radius: 10px;
            padding: 10px;
            font-size: 14px;
        """)

        # Layout for text
        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.text_label)
        layout.addStretch()

        # Initialize with hidden state
        self.hide()

    def rotate(self):
        self.angle = (self.angle + 9) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent background
        painter.fillRect(event.rect(), QColor(255, 255, 255, 180))

        # Draw loading spinner
        center = QPoint(self.width() // 2, self.height() // 2 - 40)
        radius = 30
        painter.translate(center)
        painter.rotate(self.angle)

        for i in range(8):
            painter.save()
            painter.rotate(i * 45)
            painter.translate(radius, 0)

            alpha = 255 - (i * 32)
            if alpha < 0:
                alpha = 0

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 122, 255, alpha))
            painter.drawEllipse(-5, -5, 10, 10)
            painter.restore()

    def show_loading(self, text="Loading..."):
        self.text_label.setText(text)
        super().show()
        self.raise_()

    def hide_loading(self):
        super().hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.text_label.setGeometry(
            (self.width() - 200) // 2,
            (self.height() - 50) // 2 + 50,
            200, 50
        )


# Animated button class for a modern look
class AnimatedButton(QPushButton):
    # Correct signal declaration as class attributes
    _hover_value_changed = pyqtSignal()
    _press_value_changed = pyqtSignal()

    def __init__(self, text, parent=None, icon=None):
        super().__init__(text, parent)

        if icon:
            self.setIcon(icon)

        self.setMinimumHeight(36)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Shadow effect
        self.shadow_effect = None
        self.apply_shadow(2)

        # Animation properties
        self._hover_animation = QPropertyAnimation(self, b"_hover_value")
        self._hover_animation.setDuration(200)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._press_animation = QPropertyAnimation(self, b"_press_value")
        self._press_animation.setDuration(100)

        self._hover_value = 0
        self._press_value = 0

    def apply_shadow(self, blur_radius=5):
        """Apply drop shadow effect to the button"""
        if self.shadow_effect is None:
            from PyQt6.QtWidgets import QGraphicsDropShadowEffect
            self.shadow_effect = QGraphicsDropShadowEffect(self)
            self.shadow_effect.setBlurRadius(blur_radius)
            self.shadow_effect.setColor(QColor(0, 0, 0, 50))
            self.shadow_effect.setOffset(0, 2)
            self.setGraphicsEffect(self.shadow_effect)

    def remove_shadow(self):
        """Remove the shadow effect"""
        if self.shadow_effect:
            self.setGraphicsEffect(None)
            self.shadow_effect = None

    # Property for animations
    def _get_hover_value(self):
        return self._hover_value

    def _set_hover_value(self, value):
        self._hover_value = value
        self.update()

    _hover_value = property(_get_hover_value, _set_hover_value)

    def _get_press_value(self):
        return self._press_value

    def _set_press_value(self, value):
        self._press_value = value
        self.update()

    _press_value = property(_get_press_value, _set_press_value)

    def enterEvent(self, event):
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_value)
        self._hover_animation.setEndValue(1)
        self._hover_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_value)
        self._hover_animation.setEndValue(0)
        self._hover_animation.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_animation.stop()
            self._press_animation.setStartValue(self._press_value)
            self._press_animation.setEndValue(1)
            self._press_animation.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_animation.stop()
            self._press_animation.setStartValue(self._press_value)
            self._press_animation.setEndValue(0)
            self._press_animation.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        # For custom painting in the future if needed
        super().paintEvent(event)


# Button with dropdown menu
class DropdownButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(36)
        self.menu = QMenu(self)
        self.setMenu(self.menu)

        # Style the button
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def add_action(self, text, callback):
        action = QAction(text, self)
        action.triggered.connect(callback)
        self.menu.addAction(action)
        return action


# Custom file tree widget with checkbox support
class FileTreeWidget(QTreeWidget):
    fileClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setAnimated(True)
        self.setHeaderLabels(["File/Folder", "Type", "Size"])
        self.setColumnWidth(0, 300)

        # Improve hit test areas for checkboxes
        self.checkbox_rect_cache = {}

        # Enable drag and drop for file ordering
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

        # Store root path for lazy loading
        self.root_path = ""

        # Track ignored/included items (set of full paths)
        self.ignored_items = set()

        # Store extension filter state
        self.ignored_extensions = set()

        # Reverse ignore mode (include only selected items)
        self.reverse_ignore_mode = False

        # Cache for loaded directories to avoid re-scanning
        self.loaded_directories = set()

        # Cache icons to avoid expensive style().standardIcon() calls
        self._icon_cache = {
            'folder': self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon),
            'file': self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon),
            'binary': self.style().standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon)
        }

        # Connect signals
        self.itemClicked.connect(self.handle_item_clicked)
        self.itemExpanded.connect(self.on_item_expanded)

    def handle_item_clicked(self, item, column):
        # Get click position
        pos = self.mapFromGlobal(QCursor.pos())

        # Get item rect and check if click was in the checkbox area
        rect = self.visualItemRect(item)

        # Checkbox is typically in the first 20-25 pixels of the item
        checkbox_rect = QRect(rect.left() + 2, rect.top() + 2, 20, rect.height() - 4)

        # If click was in the checkbox area, toggle the checkbox state
        if checkbox_rect.contains(pos) and column == 0 and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
            current_state = item.checkState(0)
            new_state = Qt.CheckState.Unchecked if current_state == Qt.CheckState.Checked else Qt.CheckState.Checked
            item.setCheckState(0, new_state)
        else:
            # Otherwise emit signal for file click
            if item.text(1) == "text":
                # Use the new get_item_path method for consistency
                full_path = self.get_item_path(item)
                self.fileClicked.emit(full_path)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            # Get item rect and check if click was in the checkbox area
            rect = self.visualItemRect(item)

            # Checkbox is typically in the first 20-25 pixels of the item
            checkbox_rect = QRect(rect.left() + 2, rect.top() + 2, 20, rect.height() - 4)

            if checkbox_rect.contains(event.pos()) and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                # Handle in clicked event
                super().mousePressEvent(event)
            else:
                # Pass to parent for selection
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def get_item_path(self, item):
        """Get the full filesystem path for a tree item."""
        path_parts = []
        temp_item = item
        while temp_item is not None:
            path_parts.insert(0, temp_item.text(0))
            temp_item = temp_item.parent()

        # Skip the root item name which is just the folder name
        if len(path_parts) > 1:
            path_parts.pop(0)
            return os.path.join(self.root_path, *path_parts)
        else:
            return self.root_path

    def on_item_expanded(self, item):
        """Lazy load folder contents when a folder is expanded."""
        # Get the full path of this item
        item_path = self.get_item_path(item)

        # Check if this directory has already been loaded
        if item_path in self.loaded_directories:
            return

        # Mark as loaded to avoid re-scanning
        self.loaded_directories.add(item_path)

        # Remove placeholder if it exists
        if item.childCount() == 1 and item.child(0).text(0) == "Loading...":
            item.removeChild(item.child(0))

        # Load contents
        self.load_folder_contents(item, item_path)

        # Trigger extension collection update in main window
        # This is a bit hacky, but we need to notify the main window
        try:
            main_window = self.parent()
            while main_window and not isinstance(main_window, QMainWindow):
                main_window = main_window.parent()
            if main_window and hasattr(main_window, 'collect_and_display_extensions'):
                main_window.collect_and_display_extensions()
        except:
            pass  # Silently fail if we can't find the main window

    @log_performance
    def load_folder_contents(self, parent_item, folder_path):
        """Load the immediate contents of a folder (non-recursive)."""
        perf_logger.info(f"Loading folder: {folder_path}")
        start_time = time.perf_counter()

        # Block signals during initial load to prevent cascade
        self.blockSignals(True)

        try:
            path = Path(folder_path)
            if not path.exists() or not path.is_dir():
                logger.warning(f"Folder does not exist or is not a directory: {folder_path}")
                return

            # List directory contents
            list_start = time.perf_counter()
            try:
                items = list(path.iterdir())
            except PermissionError as e:
                logger.error(f"Permission denied accessing folder: {folder_path}")
                return
            list_elapsed = time.perf_counter() - list_start
            perf_logger.debug(f"Directory listing took {list_elapsed:.4f}s for {len(items)} items")

            # Sort: directories first, then files alphabetically
            sort_start = time.perf_counter()
            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            sort_elapsed = time.perf_counter() - sort_start
            perf_logger.debug(f"Sorting took {sort_elapsed:.4f}s")

            files_processed = 0
            dirs_processed = 0

            for item_path in items:
                try:
                    item_name = item_path.name

                    if item_path.is_dir():
                        # Create directory item
                        dir_item = QTreeWidgetItem(parent_item, [item_name, "folder", ""])
                        dir_item.setIcon(0, self._icon_cache['folder'])
                        dir_item.setFlags(dir_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

                        # Set initial check state based on ignore mode
                        # Simple: Normal mode = checked, Reverse mode = unchecked
                        initial_state = Qt.CheckState.Unchecked if self.reverse_ignore_mode else Qt.CheckState.Checked
                        dir_item.setCheckState(0, initial_state)

                        # Add a placeholder child to make it expandable
                        placeholder = QTreeWidgetItem(dir_item, ["Loading...", "", ""])
                        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)

                        dirs_processed += 1

                    else:
                        # Get file extension
                        extension = item_path.suffix.lower()

                        # Skip if extension is ignored
                        if extension in self.ignored_extensions:
                            continue

                        # OPTIMIZATION: Skip expensive is_text_file check during initial load
                        # Instead, do a quick heuristic based on extension
                        file_type = self._quick_file_type_check(item_path)

                        # Get file size (fast operation)
                        try:
                            file_size = item_path.stat().st_size
                            size_str = self.format_file_size(file_size)
                        except:
                            size_str = "?"

                        # Create file item
                        file_item = QTreeWidgetItem(parent_item, [item_name, file_type, size_str])

                        # Set icon based on type (using cached icons)
                        if file_type == "text":
                            file_item.setIcon(0, self._icon_cache['file'])
                        else:
                            file_item.setIcon(0, self._icon_cache['binary'])

                        # Make checkable
                        file_item.setFlags(file_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

                        # Set initial check state
                        # Simple: Normal mode = checked, Reverse mode = unchecked
                        initial_state = Qt.CheckState.Unchecked if self.reverse_ignore_mode else Qt.CheckState.Checked
                        file_item.setCheckState(0, initial_state)

                        files_processed += 1

                except Exception as e:
                    logger.error(f"Error processing {item_path}: {e}")
                    logger.debug(traceback.format_exc())
                    continue

            elapsed = time.perf_counter() - start_time
            perf_logger.info(f"Loaded {dirs_processed} dirs and {files_processed} files in {elapsed:.4f}s")

        except Exception as e:
            logger.error(f"Error loading folder {folder_path}: {e}")
            logger.debug(traceback.format_exc())
        finally:
            # Always unblock signals
            self.blockSignals(False)

    def _quick_file_type_check(self, file_path):
        """Fast heuristic to determine if file is likely text or binary based on extension."""
        # Common text file extensions
        text_extensions = {
            '.txt', '.py', '.js', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.rb',
            '.go', '.rs', '.php', '.html', '.css', '.scss', '.sass', '.xml', '.json',
            '.yaml', '.yml', '.md', '.rst', '.tex', '.sh', '.bash', '.ps1', '.bat',
            '.sql', '.r', '.m', '.swift', '.kt', '.ts', '.jsx', '.tsx', '.vue',
            '.toml', '.ini', '.cfg', '.conf', '.properties', '.env', '.gitignore',
            '.dockerfile', '.makefile', '.cmake', '.gradle', '.sbt', '.maven'
        }

        ext = file_path.suffix.lower()
        if ext in text_extensions:
            return "text"

        # If unknown, mark as binary (safer default)
        # Can be verified later when actually processing
        return "binary"

    def format_file_size(self, size):
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    @log_performance
    def set_root_folder(self, folder_path):
        """Initialize the tree with a root folder (lazy loading)."""
        logger.info(f"Setting root folder: {folder_path}")
        perf_logger.info(f"Root folder: {folder_path}")

        self.clear()
        self.root_path = folder_path
        self.loaded_directories.clear()
        self.ignored_items.clear()

        # Block signals during root setup to prevent cascade
        self.blockSignals(True)

        # Create root item
        root_name = os.path.basename(folder_path)
        root_item = QTreeWidgetItem(self, [root_name, "folder", ""])
        root_item.setIcon(0, self._icon_cache['folder'])
        root_item.setFlags(root_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        root_item.setCheckState(0, Qt.CheckState.Checked if not self.reverse_ignore_mode else Qt.CheckState.Unchecked)

        # Load immediate contents of root
        self.loaded_directories.add(folder_path)
        self.load_folder_contents(root_item, folder_path)

        # Unblock signals before expanding (expansion should be normal)
        self.blockSignals(False)

        # Expand root
        self.expandItem(root_item)

        logger.info(f"Root folder loaded successfully")


# Custom status bar with animation support
class AnimatedStatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize alpha BEFORE creating QPropertyAnimation (animation needs to read the property)
        self.__alpha = 255  # Use double underscore for internal storage
        self._temp_message = ""
        self._base_message = ""

        # Animation properties (created AFTER __alpha is initialized)
        self.fade_animation = QPropertyAnimation(self, b"_alpha")
        self.fade_animation.setDuration(500)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.finished.connect(self._on_fade_finished)

        # Style
        self.setStyleSheet("""
            QStatusBar {
                border-top: 1px solid #e0e0e0;
                padding: 4px;
                background-color: #f8f8f8;
            }
        """)

    # Property for animation - using pyqtProperty for Qt's meta-object system
    def get_alpha(self):
        return self.__alpha

    def set_alpha(self, value):
        self.__alpha = value
        self.update()

    _alpha = pyqtProperty(int, fget=get_alpha, fset=set_alpha)

    def _on_fade_finished(self):
        if self._alpha == 0:
            super().showMessage(self._base_message)
            self.fade_animation.setStartValue(0)
            self.fade_animation.setEndValue(255)
            self.fade_animation.start()

    def showMessage(self, message, timeout=0):
        self._base_message = message
        super().showMessage(message)

    def showTemporaryMessage(self, message, timeout=2000):
        self._temp_message = message

        # Stop any current animation
        self.fade_animation.stop()

        # Show temporary message
        super().showMessage(message)

        # Start fade out animation after timeout
        QTimer.singleShot(timeout, self._start_fade_out)

    def _start_fade_out(self):
        self.fade_animation.setStartValue(255)
        self.fade_animation.setEndValue(0)
        self.fade_animation.start()

    def paintEvent(self, event):
        super().paintEvent(event)

        # If we're animating a fade, apply transparency
        if self.fade_animation.state() == QPropertyAnimation.State.Running:
            painter = QPainter(self)
            painter.setOpacity(self._alpha / 255.0)
            painter.fillRect(event.rect(), QColor(248, 248, 248, 128))


# Worker thread for processing files
class FileProcessorWorker(QObject):
    progress = pyqtSignal(int, int)  # current, total
    file_found = pyqtSignal(str, str)  # path, file_type
    processing_complete = pyqtSignal(bool, str)  # success, message
    current_file = pyqtSignal(str)  # current file being processed

    def __init__(self, root_folder, excluded_paths, output_file, separator_style, file_list=None):
        super().__init__()
        self.root_folder = root_folder
        self.excluded_paths = excluded_paths
        self.output_file = output_file
        self.separator_style = separator_style
        self.file_list = file_list  # Optional: if provided, use this instead of scanning
        self.cancelled = False
        self.use_parallel = CPU_COUNT > 1  # Use parallel processing if multi-core

    def _read_file_parallel(self, file_path):
        """Read a single file (for parallel processing)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return (file_path, f.read(), None)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return (file_path, None, str(e))

    @log_performance
    def process_files(self):
        try:
            # If file list is provided, use it directly (lazy loading mode)
            if self.file_list is not None:
                text_files = self.file_list
            else:
                # Legacy mode: scan file system
                text_files = []

                # Emit initial progress
                self.progress.emit(0, 0)

                # Find all text files
                for root, dirs, files in os.walk(self.root_folder):
                    # Skip excluded directories
                    dirs[:] = [d for d in dirs if os.path.join(root, d) not in self.excluded_paths]

                    for file in files:
                        file_path = os.path.join(root, file)

                        # Skip excluded files
                        if file_path in self.excluded_paths:
                            continue

                        self.current_file.emit(file_path)

                        if is_text_file(file_path):
                            text_files.append(file_path)
                            rel_path = os.path.relpath(file_path, self.root_folder)
                            self.file_found.emit(file_path, "text")

                        if self.cancelled:
                            self.processing_complete.emit(False, "Operation cancelled")
                            return

            total_files = len(text_files)
            self.progress.emit(0, total_files)

            logger.info(f"Processing {total_files} files with parallel={self.use_parallel}")
            perf_logger.info(f"Starting file processing: {total_files} files, parallel={self.use_parallel}")

            # Read all files in parallel (if enabled)
            file_contents = {}
            if self.use_parallel and total_files > 10:  # Only use parallel for > 10 files
                perf_logger.info(f"Using parallel file reading with {min(CPU_COUNT, 8)} workers")
                # Use ThreadPoolExecutor for parallel file I/O
                with ThreadPoolExecutor(max_workers=min(CPU_COUNT, 8)) as executor:
                    futures = {executor.submit(self._read_file_parallel, fp): fp for fp in text_files}

                    for i, future in enumerate(futures):
                        if self.cancelled:
                            executor.shutdown(wait=False, cancel_futures=True)
                            self.processing_complete.emit(False, "Operation cancelled")
                            return

                        file_path, content, error = future.result()
                        file_contents[file_path] = (content, error)
                        self.progress.emit(i + 1, total_files)
                        self.current_file.emit(f"Reading: {os.path.relpath(file_path, self.root_folder)}")
            else:
                # Sequential file reading for small numbers of files
                perf_logger.info("Using sequential file reading")
                for i, file_path in enumerate(text_files):
                    if self.cancelled:
                        self.processing_complete.emit(False, "Operation cancelled")
                        return

                    _, content, error = self._read_file_parallel(file_path)
                    file_contents[file_path] = (content, error)
                    self.progress.emit(i + 1, total_files)
                    self.current_file.emit(f"Reading: {os.path.relpath(file_path, self.root_folder)}")

            # Now write the combined output file
            perf_logger.info("Writing combined output file")
            with open(self.output_file, 'w', encoding='utf-8') as output:
                # Write a header at the top of the file
                output.write(f"# Combined Code from {os.path.basename(self.root_folder)}\n")
                output.write(f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                output.write(f"# Contains {total_files} text files\n\n")

                for i, file_path in enumerate(text_files):
                    if self.cancelled:
                        self.processing_complete.emit(False, "Operation cancelled")
                        return

                    rel_path = os.path.relpath(file_path, self.root_folder)
                    self.current_file.emit(f"Writing: {rel_path}")

                    # Add separator and file info
                    if self.separator_style == "Simple":
                        separator = f"\n\n{'=' * 80}\n"
                        header = f"FILE: {rel_path}\n{'=' * 80}\n\n"
                        footer = ""
                    elif self.separator_style == "Detailed":
                        try:
                            file_size = os.path.getsize(file_path)
                            file_time = os.path.getmtime(file_path)
                            timestamp = datetime.fromtimestamp(file_time).strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            file_size = 0
                            timestamp = "Unknown"

                        separator = f"\n\n{'=' * 80}\n"
                        header = f"FILE: {rel_path}\n"
                        header += f"SIZE: {file_size} bytes\n"
                        header += f"MODIFIED: {timestamp}\n"
                        header += f"{'=' * 80}\n\n"
                        footer = ""
                    else:  # Markdown
                        separator = f"\n\n"
                        ext = os.path.splitext(file_path)[1][1:] or "text"
                        header = f"## {rel_path}\n\n```{ext}\n"
                        footer = "\n```\n"

                    output.write(separator)
                    output.write(header)

                    # Write file content (already read)
                    content, error = file_contents.get(file_path, (None, "File not found"))
                    if content is not None:
                        output.write(content)
                    else:
                        output.write(f"\n[Error reading file: {error}]\n")
                        logger.warning(f"Failed to read file {file_path}: {error}")

                    # Write footer if needed
                    output.write(footer)

                    # Slight pause to prevent UI freezing on very fast systems
                    QCoreApplication.processEvents()

                    # Update progress
                    self.progress.emit(i + 1, total_files)

            self.processing_complete.emit(True,
                                          f"Successfully processed {total_files} files. Output saved to {self.output_file}")

        except Exception as e:
            self.processing_complete.emit(False, f"Error: {str(e)}")

    def cancel(self):
        self.cancelled = True


# Custom dialog for showing preferences
class PreferencesDialog(QDialog):
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        # Appearance group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)

        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "System"])
        appearance_layout.addRow("Theme:", self.theme_combo)

        # Font selector
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 20)
        self.font_size_spin.setValue(10)
        appearance_layout.addRow("Code Font Size:", self.font_size_spin)

        layout.addWidget(appearance_group)

        # File processing group
        processing_group = QGroupBox("File Processing")
        processing_layout = QFormLayout(processing_group)

        # Default output format
        self.default_format_combo = QComboBox()
        self.default_format_combo.addItems(["Simple", "Detailed", "Markdown"])
        processing_layout.addRow("Default Format:", self.default_format_combo)

        # Auto-exclude patterns
        self.exclude_patterns_edit = QLineEdit()
        self.exclude_patterns_edit.setPlaceholderText("e.g. *.pyc, __pycache__, .git")
        processing_layout.addRow("Auto-exclude Patterns:", self.exclude_patterns_edit)

        layout.addWidget(processing_group)

        # Advanced group
        advanced_group = QGroupBox("Advanced")
        advanced_layout = QFormLayout(advanced_group)

        # Concurrency
        self.concurrency_spin = QSpinBox()
        self.concurrency_spin.setRange(1, 16)
        self.concurrency_spin.setValue(1)
        advanced_layout.addRow("Concurrency:", self.concurrency_spin)

        # Backup
        self.backup_check = QCheckBox("Create backup before processing")
        self.backup_check.setChecked(True)
        advanced_layout.addRow("", self.backup_check)

        layout.addWidget(advanced_group)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Load settings
        self.load_settings()

    def load_settings(self):
        if not self.settings:
            return

        # Load theme
        theme = self.settings.value("theme", "Light")
        index = self.theme_combo.findText(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        # Load font size
        font_size = self.settings.value("code_font_size", 10, type=int)
        self.font_size_spin.setValue(font_size)

        # Load default format
        format = self.settings.value("default_format", "Markdown")
        index = self.default_format_combo.findText(format)
        if index >= 0:
            self.default_format_combo.setCurrentIndex(index)

        # Load exclude patterns
        patterns = self.settings.value("exclude_patterns", "*.pyc, __pycache__, .git, .vscode, .idea")
        self.exclude_patterns_edit.setText(patterns)

        # Load concurrency
        concurrency = self.settings.value("concurrency", 1, type=int)
        self.concurrency_spin.setValue(concurrency)

        # Load backup setting
        backup = self.settings.value("create_backup", True, type=bool)
        self.backup_check.setChecked(backup)

    def save_settings(self):
        if not self.settings:
            return

        # Save theme
        self.settings.setValue("theme", self.theme_combo.currentText())

        # Save font size
        self.settings.setValue("code_font_size", self.font_size_spin.value())

        # Save default format
        self.settings.setValue("default_format", self.default_format_combo.currentText())

        # Save exclude patterns
        self.settings.setValue("exclude_patterns", self.exclude_patterns_edit.text())

        # Save concurrency
        self.settings.setValue("concurrency", self.concurrency_spin.value())

        # Save backup setting
        self.settings.setValue("create_backup", self.backup_check.isChecked())

    def accept(self):
        self.save_settings()
        super().accept()


# Worker thread for scanning folders
class ScanFolderWorker(QObject):
    progress_signal = pyqtSignal(str, int)  # current file, folder depth
    file_found_signal = pyqtSignal(str, str, int)  # path, type, size
    scan_complete = pyqtSignal(dict, dict)  # file tree data, file counts

    def __init__(self, root_folder):
        super().__init__()
        self.root_folder = root_folder
        self.cancelled = False

    def scan_folder(self):
        try:
            # Initialize counters
            file_counts = {"text": 0, "binary": 0, "error": 0}

            # Build file tree recursively
            tree_data = {}
            self._scan_directory(self.root_folder, tree_data, file_counts)

            # Emit completion signal with tree data and counts
            self.scan_complete.emit(tree_data, file_counts)

        except Exception as e:
            # Handle any exceptions
            print(f"Error scanning folder: {str(e)}")
            self.scan_complete.emit({}, {"text": 0, "binary": 0, "error": 1})

    def _scan_directory(self, directory, parent_data, file_counts):
        path = Path(directory)
        items = list(path.iterdir())

        # Get the number of subdirectories (for progress estimation)
        subdir_count = sum(1 for item in items if item.is_dir())

        # Sort items: directories first, then files alphabetically
        items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

        for item in items:
            if self.cancelled:
                return

            try:
                item_name = item.name

                # Emit progress update
                self.progress_signal.emit(str(item), subdir_count)

                if item.is_dir():
                    # Create directory entry in parent data
                    parent_data[item_name] = {
                        "is_dir": True,
                        "children": {}
                    }

                    # Recursively scan subdirectory
                    self._scan_directory(item, parent_data[item_name]["children"], file_counts)

                else:
                    # Process file
                    file_size = item.stat().st_size

                    # Determine if it's a text file
                    file_path = str(item)
                    is_text = is_text_file(file_path)
                    file_type = "text" if is_text else "binary"

                    # Update counters
                    if is_text:
                        file_counts["text"] += 1
                    else:
                        file_counts["binary"] += 1

                    # Emit file found signal
                    self.file_found_signal.emit(file_path, file_type, file_size)

                    # Add to parent data
                    parent_data[item_name] = {
                        "is_dir": False,
                        "type": file_type,
                        "size": file_size
                    }

            except Exception as e:
                # Handle any errors with individual files
                file_counts["error"] += 1
                parent_data[item.name] = {
                    "is_dir": False,
                    "type": "error",
                    "error": str(e),
                    "size": 0
                }

    def cancel(self):
        self.cancelled = True


# Main application window
class CodeCombinerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize main window
        self.setWindowTitle("Code Combiner")
        self.setMinimumSize(1000, 700)

        # Set application icon
        app_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder)
        self.setWindowIcon(app_icon)

        # Initialize settings object BEFORE UI (UI needs settings object for recent projects)
        self.settings = QSettings("CodeCombiner", "CodeCombinerApp")

        # Initialize UI (creates all widgets)
        self.init_ui()

        # Load settings into UI widgets AFTER UI is created
        self.init_settings()

        # Initialize member variables
        self.worker_thread = None
        self.worker = None
        self.file_list = []
        self.excluded_paths = set()
        self.loading_overlay = LoadingOverlay(self.central_widget)

        # Add loading indicator (initially hidden)
        self.loading_overlay.hide()

        # Apply stylesheet
        self.setStyleSheet(APP_STYLESHEET)

        # Show a welcome message
        QTimer.singleShot(500, self.show_welcome_message)

    def show_welcome_message(self):
        self.statusBar().showMessage("Welcome to Code Combiner. Select a project folder to begin.")

    def init_settings(self):
        # Load folder paths
        last_dir = self.settings.value("last_folder", QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation))
        last_output = self.settings.value("last_output", os.path.join(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation), "combined_code.txt"))

        # Load separator style
        separator_style = self.settings.value("separator_style", "Markdown")

        # Apply loaded settings
        self.input_folder_edit.setText(last_dir)
        self.output_file_edit.setText(last_output)

        index = self.separator_style_combo.findText(separator_style)
        if index >= 0:
            self.separator_style_combo.setCurrentIndex(index)

        # Load theme preference
        theme = self.settings.value("theme", "Light")
        self.apply_theme(theme)

        # Load code font size
        font_size = self.settings.value("code_font_size", 10, type=int)
        font = QFont("Consolas", font_size)
        self.preview_edit.setFont(font)

    def save_settings(self):
        # Save paths
        self.settings.setValue("last_folder", self.input_folder_edit.text())
        self.settings.setValue("last_output", self.output_file_edit.text())

        # Save separator style
        self.settings.setValue("separator_style", self.separator_style_combo.currentText())

    def apply_theme(self, theme_name):
        if theme_name == "Dark":
            # ToDo: Implement dark theme stylesheet
            pass
        elif theme_name == "System":
            # Use system theme
            QApplication.setStyle(QStyleFactory.create("Fusion"))
        else:
            # Use default light theme
            QApplication.setStyle(QStyleFactory.create("Fusion"))
            app.setStyleSheet(APP_STYLESHEET)

    def init_ui(self):
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Create header section
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # App title
        title_label = QLabel("Code Combiner")
        title_label.setProperty("title", "true")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)

        # App description
        description = QLabel(
            "Combine multiple code files into a single document with clear organization and formatting."
        )
        description.setProperty("subtitle", "true")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(description)

        main_layout.addWidget(header_widget)

        # Create main content layout with splitter
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setChildrenCollapsible(False)

        # Left panel - controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Input folder selection
        input_group = QGroupBox("Project Folder")
        input_layout = QVBoxLayout(input_group)

        input_form = QFormLayout()
        self.input_folder_edit = QLineEdit()
        self.input_folder_edit.setPlaceholderText("Select the root folder of your project")

        browse_input_btn = QPushButton("Browse...")
        browse_input_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        browse_input_btn.clicked.connect(self.browse_input_folder)

        input_folder_layout = QHBoxLayout()
        input_folder_layout.addWidget(self.input_folder_edit)
        input_folder_layout.addWidget(browse_input_btn)

        input_layout.addLayout(input_folder_layout)

        # Scan button
        scan_btn = QPushButton("Scan Folder")
        scan_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        scan_btn.clicked.connect(self.scan_folder)
        input_layout.addWidget(scan_btn)

        left_layout.addWidget(input_group)

        # Output file configuration
        output_group = QGroupBox("Output Configuration")
        output_layout = QVBoxLayout(output_group)

        # Output file path
        output_file_layout = QHBoxLayout()
        self.output_file_edit = QLineEdit()
        self.output_file_edit.setPlaceholderText("Path for the combined output file")

        browse_output_btn = QPushButton("Browse...")
        browse_output_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        browse_output_btn.clicked.connect(self.browse_output_file)

        output_file_layout.addWidget(self.output_file_edit)
        output_file_layout.addWidget(browse_output_btn)
        output_layout.addLayout(output_file_layout)

        # Separator style
        separator_layout = QHBoxLayout()
        separator_label = QLabel("Separator Style:")
        self.separator_style_combo = QComboBox()
        self.separator_style_combo.addItems(["Simple", "Detailed", "Markdown"])
        self.separator_style_combo.setCurrentText("Markdown")

        # Add tooltips
        self.separator_style_combo.setItemData(0, "Basic separators between files with minimal metadata",
                                               Qt.ItemDataRole.ToolTipRole)
        self.separator_style_combo.setItemData(1,
                                               "Detailed separators with file metadata like size and modification date",
                                               Qt.ItemDataRole.ToolTipRole)
        self.separator_style_combo.setItemData(2,
                                               "Format output as Markdown document with syntax-highlighted code blocks",
                                               Qt.ItemDataRole.ToolTipRole)

        separator_layout.addWidget(separator_label)
        separator_layout.addWidget(self.separator_style_combo, 1)
        output_layout.addLayout(separator_layout)

        left_layout.addWidget(output_group)

        # File processing
        process_group = QGroupBox("Processing")
        process_layout = QVBoxLayout(process_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        process_layout.addWidget(self.progress_bar)

        # Current file label
        self.current_file_label = QLabel("Ready")
        self.current_file_label.setWordWrap(True)
        self.current_file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        process_layout.addWidget(self.current_file_label)

        # Processing buttons
        buttons_layout = QHBoxLayout()

        # Process button
        self.process_btn = QPushButton("Combine Files")
        self.process_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.process_btn.clicked.connect(self.start_processing)
        self.process_btn.setEnabled(False)
        buttons_layout.addWidget(self.process_btn)

        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.cancel_btn.clicked.connect(self.cancel_processing)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("background-color: #ff3b30;")
        buttons_layout.addWidget(self.cancel_btn)

        process_layout.addLayout(buttons_layout)

        left_layout.addWidget(process_group)

        # Extra actions
        actions_layout = QHBoxLayout()

        # Select All / None buttons
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.select_all_btn.clicked.connect(self.select_all_files)
        self.select_all_btn.setEnabled(False)
        actions_layout.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        self.select_none_btn.clicked.connect(self.deselect_all_files)
        self.select_none_btn.setEnabled(False)
        actions_layout.addWidget(self.select_none_btn)

        left_layout.addLayout(actions_layout)

        # Add stretch to push everything up
        left_layout.addStretch()

        # Add the panel to splitter
        content_splitter.addWidget(left_panel)

        # Right panel with tabs
        right_panel = QTabWidget()
        right_panel.setDocumentMode(True)

        # File tree tab
        file_tree_tab = QWidget()
        file_tree_layout = QVBoxLayout(file_tree_tab)
        file_tree_layout.setContentsMargins(5, 5, 5, 5)

        # Filter bar for file tree
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter:")
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter files by name or extension...")
        self.filter_edit.textChanged.connect(self.filter_files)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_edit)

        file_tree_layout.addLayout(filter_layout)

        # Ignore mode toggle
        ignore_mode_layout = QHBoxLayout()
        self.reverse_ignore_checkbox = QCheckBox("Reverse Ignore Mode (Include only selected)")
        self.reverse_ignore_checkbox.setToolTip("When enabled, all files/folders are ignored except those you explicitly check")
        self.reverse_ignore_checkbox.stateChanged.connect(self.toggle_reverse_ignore_mode)
        ignore_mode_layout.addWidget(self.reverse_ignore_checkbox)
        ignore_mode_layout.addStretch()

        file_tree_layout.addLayout(ignore_mode_layout)

        # Extension filter group
        extension_filter_group = QGroupBox("File Type Filters")
        extension_filter_layout = QVBoxLayout(extension_filter_group)
        extension_filter_layout.setContentsMargins(5, 10, 5, 5)

        # Container for extension checkboxes (will be populated after scan)
        self.extension_checkboxes_widget = QWidget()
        self.extension_checkboxes_layout = QHBoxLayout(self.extension_checkboxes_widget)
        self.extension_checkboxes_layout.setContentsMargins(0, 0, 0, 0)
        self.extension_checkboxes_layout.setSpacing(5)

        # Scroll area for extension checkboxes
        extension_scroll = QScrollArea()
        extension_scroll.setWidget(self.extension_checkboxes_widget)
        extension_scroll.setWidgetResizable(True)
        extension_scroll.setMaximumHeight(80)
        extension_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        extension_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        extension_filter_layout.addWidget(extension_scroll)

        # Extension filter helper text
        extension_help = QLabel("Check/uncheck to filter file types. Scans folders as you expand them.")
        extension_help.setWordWrap(True)
        extension_help.setStyleSheet("color: #666; font-size: 9pt;")
        extension_filter_layout.addWidget(extension_help)

        file_tree_layout.addWidget(extension_filter_group)

        # File tree widget
        self.file_tree_widget = FileTreeWidget()
        self.file_tree_widget.fileClicked.connect(self._preview_file)

        # Connect to item changed for exclusion list
        self.file_tree_widget.itemChanged.connect(self.update_exclusion_list)

        # Store extension checkboxes for later reference
        self.extension_checkboxes = {}

        file_tree_layout.addWidget(self.file_tree_widget)
        right_panel.addTab(file_tree_tab, "Files")

        # Preview tab
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        preview_layout.setContentsMargins(5, 5, 5, 5)

        # Preview toolbar
        preview_toolbar = QHBoxLayout()

        # File name label
        self.preview_file_label = QLabel("No file selected")
        self.preview_file_label.setWordWrap(True)
        preview_toolbar.addWidget(self.preview_file_label, 1)

        preview_layout.addLayout(preview_toolbar)

        # Preview text area
        self.preview_edit = QTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setFont(QFont("Consolas", 10))
        self.preview_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Add syntax highlighter
        self.syntax_highlighter = CodeSyntaxHighlighter(self.preview_edit.document())

        preview_layout.addWidget(self.preview_edit)
        right_panel.addTab(preview_tab, "Preview")

        # Output preview tab
        output_preview_tab = QWidget()
        output_preview_layout = QVBoxLayout(output_preview_tab)
        output_preview_layout.setContentsMargins(5, 5, 5, 5)

        # Output preview text area
        self.output_preview_edit = QTextEdit()
        self.output_preview_edit.setReadOnly(True)
        self.output_preview_edit.setFont(QFont("Consolas", 10))
        self.output_preview_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.output_preview_edit.setPlaceholderText("Process files to see a preview of the combined output")

        output_preview_layout.addWidget(self.output_preview_edit)
        right_panel.addTab(output_preview_tab, "Output Preview")

        # Help tab
        help_tab = QWidget()
        help_layout = QVBoxLayout(help_tab)
        help_layout.setContentsMargins(5, 5, 5, 5)

        # Create scrollable help content
        help_scroll = QScrollArea()
        help_scroll.setWidgetResizable(True)
        help_scroll.setFrameShape(QFrame.Shape.NoFrame)

        help_content = QWidget()
        help_content_layout = QVBoxLayout(help_content)

        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setFrameShape(QFrame.Shape.NoFrame)

        help_html = """
        <h2>Code Combiner Help</h2>
        <p>This tool helps you combine multiple code files into a single text file for easier analysis or sharing.</p>

        <h3>How to Use:</h3>
        <ol>
            <li><b>Select Project Folder:</b> Click "Browse..." to select the root folder of your project.</li>
            <li><b>Scan Folder:</b> Click "Scan Folder" to locate all text files in the project.</li>
            <li><b>Select Files to Include:</b> In the Files tab, check/uncheck files to include/exclude.</li>
            <li><b>Set Output Location:</b> Specify where the combined file should be saved.</li>
            <li><b>Choose Separator Style:</b>
                <ul>
                    <li><b>Simple:</b> Basic separators with file paths</li>
                    <li><b>Detailed:</b> Include file metadata like size and modification date</li>
                    <li><b>Markdown:</b> Format output as a Markdown document with code blocks</li>
                </ul>
            </li>
            <li><b>Combine Files:</b> Click "Combine Files" to generate the output file.</li>
        </ol>

        <h3>Tips:</h3>
        <ul>
            <li>The tool automatically detects text files but you can manually select/deselect files.</li>
            <li>To exclude an entire folder, uncheck it in the file tree.</li>
            <li>Preview the content of individual files by clicking on them in the Files tab.</li>
            <li>Use the filter box to quickly find specific files.</li>
            <li>Use "Select All" or "Select None" buttons to quickly check/uncheck all files.</li>
            <li>The "Output Preview" tab shows how your combined file will look.</li>
            <li>Use "Cancel" to stop a running operation at any time.</li>
        </ul>

        <h3>Keyboard Shortcuts:</h3>
        <table>
            <tr><td><b>Ctrl+O</b></td><td>Select Project Folder</td></tr>
            <tr><td><b>Ctrl+S</b></td><td>Scan Folder</td></tr>
            <tr><td><b>Ctrl+R</b></td><td>Combine Files</td></tr>
            <tr><td><b>Ctrl+F</b></td><td>Focus Filter Box</td></tr>
            <tr><td><b>Ctrl+A</b></td><td>Select All Files</td></tr>
            <tr><td><b>Ctrl+N</b></td><td>Select None</td></tr>
            <tr><td><b>Ctrl+P</b></td><td>Show Preferences</td></tr>
            <tr><td><b>F1</b></td><td>Show Help</td></tr>
            <tr><td><b>Esc</b></td><td>Cancel Operation</td></tr>
        </table>
        """

        help_text.setHtml(help_html)
        help_content_layout.addWidget(help_text)

        help_scroll.setWidget(help_content)
        help_layout.addWidget(help_scroll)

        right_panel.addTab(help_tab, "Help")

        # Add panels to splitter
        content_splitter.addWidget(right_panel)

        # Set initial splitter sizes
        content_splitter.setSizes([300, 700])

        # Add splitter to main layout
        main_layout.addWidget(content_splitter, 1)

        # Create status bar with animation support
        self.status_bar = AnimatedStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Create menu bar
        self.create_menu_bar()

        # Create keyboard shortcuts
        self.create_shortcuts()

    def create_menu_bar(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        # Select Folder action
        open_action = QAction("Select Folder...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        open_action.triggered.connect(self.browse_input_folder)
        file_menu.addAction(open_action)

        # Scan Folder action
        scan_action = QAction("Scan Folder", self)
        scan_action.setShortcut("Ctrl+S")
        scan_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        scan_action.triggered.connect(self.scan_folder)
        file_menu.addAction(scan_action)

        # Select Output File action
        output_action = QAction("Select Output File...", self)
        output_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        output_action.triggered.connect(self.browse_output_file)
        file_menu.addAction(output_action)

        file_menu.addSeparator()

        # Combine Files action
        combine_action = QAction("Combine Files", self)
        combine_action.setShortcut("Ctrl+R")
        combine_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        combine_action.triggered.connect(self.start_processing)
        file_menu.addAction(combine_action)

        # Cancel action
        cancel_action = QAction("Cancel", self)
        cancel_action.setShortcut("Esc")
        cancel_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        cancel_action.triggered.connect(self.cancel_processing)
        file_menu.addAction(cancel_action)

        file_menu.addSeparator()

        # Recent files submenu
        self.recent_menu = file_menu.addMenu("Recent Projects")
        self.update_recent_menu()

        file_menu.addSeparator()

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")

        # Select All action
        select_all_action = QAction("Select All Files", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.select_all_files)
        edit_menu.addAction(select_all_action)

        # Deselect All action
        deselect_all_action = QAction("Deselect All Files", self)
        deselect_all_action.setShortcut("Ctrl+N")
        deselect_all_action.triggered.connect(self.deselect_all_files)
        edit_menu.addAction(deselect_all_action)

        edit_menu.addSeparator()

        # Focus Filter action
        filter_action = QAction("Focus Filter", self)
        filter_action.setShortcut("Ctrl+F")
        filter_action.triggered.connect(lambda: self.filter_edit.setFocus())
        edit_menu.addAction(filter_action)

        edit_menu.addSeparator()

        # Preferences action
        prefs_action = QAction("Preferences...", self)
        prefs_action.setShortcut("Ctrl+P")
        prefs_action.triggered.connect(self.show_preferences)
        edit_menu.addAction(prefs_action)

        # View menu
        view_menu = menubar.addMenu("View")

        # Files tab action
        files_action = QAction("Files Panel", self)
        files_action.setShortcut("F2")
        files_action.triggered.connect(lambda: self.central_widget.findChild(QTabWidget).setCurrentIndex(0))
        view_menu.addAction(files_action)

        # Preview tab action
        preview_action = QAction("Preview Panel", self)
        preview_action.setShortcut("F3")
        preview_action.triggered.connect(lambda: self.central_widget.findChild(QTabWidget).setCurrentIndex(1))
        view_menu.addAction(preview_action)

        # Output Preview tab action
        output_action = QAction("Output Preview", self)
        output_action.setShortcut("F4")
        output_action.triggered.connect(lambda: self.central_widget.findChild(QTabWidget).setCurrentIndex(2))
        view_menu.addAction(output_action)

        # Help tab action
        help_action = QAction("Help", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(lambda: self.central_widget.findChild(QTabWidget).setCurrentIndex(3))
        view_menu.addAction(help_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        # Quick Help action
        quick_help_action = QAction("Quick Help", self)
        quick_help_action.triggered.connect(lambda: self.central_widget.findChild(QTabWidget).setCurrentIndex(3))
        help_menu.addAction(quick_help_action)

        # About action
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def create_shortcuts(self):
        # Already have menu shortcuts, but add some extras

        # F5 to refresh/scan folder
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self.scan_folder)

        # Ctrl+Tab to cycle through tabs
        next_tab_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        next_tab_shortcut.activated.connect(self.next_tab)

        # Ctrl+Shift+Tab to cycle backwards through tabs
        prev_tab_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        prev_tab_shortcut.activated.connect(self.prev_tab)

    def next_tab(self):
        tabwidget = self.central_widget.findChild(QTabWidget)
        current = tabwidget.currentIndex()
        tabwidget.setCurrentIndex((current + 1) % tabwidget.count())

    def prev_tab(self):
        tabwidget = self.central_widget.findChild(QTabWidget)
        current = tabwidget.currentIndex()
        tabwidget.setCurrentIndex((current - 1) % tabwidget.count())

    def update_recent_menu(self):
        self.recent_menu.clear()

        # Get recent projects from settings
        recent_projects = self.settings.value("recent_projects", [])
        if not recent_projects:
            no_recent = QAction("No Recent Projects", self)
            no_recent.setEnabled(False)
            self.recent_menu.addAction(no_recent)
            return

        for project in recent_projects:
            action = QAction(project, self)
            action.triggered.connect(lambda checked, p=project: self.open_recent_project(p))
            self.recent_menu.addAction(action)

        self.recent_menu.addSeparator()

        clear_action = QAction("Clear Recent Projects", self)
        clear_action.triggered.connect(self.clear_recent_projects)
        self.recent_menu.addAction(clear_action)

    def open_recent_project(self, project_path):
        if os.path.isdir(project_path):
            self.input_folder_edit.setText(project_path)
            self.scan_folder()
        else:
            # Remove invalid path from recent projects
            self.status_bar.showTemporaryMessage(f"Project folder not found: {project_path}")
            recent_projects = self.settings.value("recent_projects", [])
            if project_path in recent_projects:
                recent_projects.remove(project_path)
                self.settings.setValue("recent_projects", recent_projects)
                self.update_recent_menu()

    def add_to_recent_projects(self, project_path):
        recent_projects = self.settings.value("recent_projects", [])
        if not isinstance(recent_projects, list):
            recent_projects = []

        # Remove if exists (to move to top)
        if project_path in recent_projects:
            recent_projects.remove(project_path)

        # Add to top of list
        recent_projects.insert(0, project_path)

        # Limit to 10 recent projects
        recent_projects = recent_projects[:10]

        # Save to settings
        self.settings.setValue("recent_projects", recent_projects)

        # Update menu
        self.update_recent_menu()

    def clear_recent_projects(self, checked=False):
        """Clear recent projects list. The checked parameter is from the signal and is ignored."""
        self.settings.setValue("recent_projects", [])
        self.update_recent_menu()

    def show_preferences(self, checked=False):
        """Show preferences dialog. The checked parameter is from the signal and is ignored."""
        dialog = PreferencesDialog(self, self.settings)
        if dialog.exec():
            # Apply settings that need immediate effect
            theme = self.settings.value("theme", "Light")
            self.apply_theme(theme)

            font_size = self.settings.value("code_font_size", 10, type=int)
            font = QFont("Consolas", font_size)
            self.preview_edit.setFont(font)
            self.output_preview_edit.setFont(font)

            # Update separator style combo if default changed
            default_format = self.settings.value("default_format", "Markdown")
            if not self.file_list:  # Only change if no files loaded
                index = self.separator_style_combo.findText(default_format)
                if index >= 0:
                    self.separator_style_combo.setCurrentIndex(index)

    def resizeEvent(self, event):
        """Resize the loading overlay when window resizes"""
        if self.loading_overlay:
            self.loading_overlay.resize(self.central_widget.size())
        super().resizeEvent(event)

    def browse_input_folder(self, checked=False):
        """Browse for input folder. The checked parameter is from the signal and is ignored."""
        current_dir = self.input_folder_edit.text()
        if not current_dir or not os.path.isdir(current_dir):
            current_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)

        folder = QFileDialog.getExistingDirectory(
            self, "Select Project Folder", current_dir,
            QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            self.input_folder_edit.setText(folder)
            self.save_settings()
            self.add_to_recent_projects(folder)

            # Auto-scan the folder
            QTimer.singleShot(100, self.scan_folder)

    def browse_output_file(self, checked=False):
        """Browse for output file. The checked parameter is from the signal and is ignored."""
        current_dir = os.path.dirname(self.output_file_edit.text())
        if not current_dir or not os.path.isdir(current_dir):
            current_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)

        default_ext = ".md" if self.separator_style_combo.currentText() == "Markdown" else ".txt"
        suggested_name = os.path.join(current_dir, f"combined_code{default_ext}")

        file, _ = QFileDialog.getSaveFileName(
            self, "Select Output File", suggested_name,
            "Text Files (*.txt);;Markdown Files (*.md);;All Files (*)"
        )

        if file:
            self.output_file_edit.setText(file)
            self.save_settings()

    @log_performance
    def scan_folder(self, checked=False):
        """Scan the selected folder. The checked parameter is from the signal and is ignored."""
        input_folder = self.input_folder_edit.text()
        logger.info(f"User initiated scan for folder: {input_folder}")

        if not input_folder or not os.path.isdir(input_folder):
            logger.warning(f"Invalid folder selected: {input_folder}")
            QMessageBox.warning(
                self, "Invalid Folder",
                "Please select a valid project folder."
            )
            return

        perf_logger.info(f"Scanning folder: {input_folder}")
        scan_start = time.perf_counter()

        # Clear previous scan results
        self.file_list = []
        self.excluded_paths = set()
        self.preview_edit.clear()
        self.output_preview_edit.clear()
        self.preview_file_label.setText("No file selected")

        # Initialize progress UI
        self.progress_bar.setValue(0)
        self.current_file_label.setText("Loading root folder...")
        self.status_bar.showMessage("Loading folder...")

        # Use lazy loading - just set root and load immediate contents
        self.file_tree_widget.set_root_folder(input_folder)

        # Collect extensions from root level (will collect more as user expands)
        self.collect_and_display_extensions()

        # Enable UI
        self.process_btn.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.select_none_btn.setEnabled(True)

        # Update status
        scan_elapsed = time.perf_counter() - scan_start
        perf_logger.info(f"Folder scan completed in {scan_elapsed:.4f}s")
        logger.info(f"Folder loaded successfully in {scan_elapsed:.4f}s")

        self.status_bar.showMessage(f"Folder loaded in {scan_elapsed:.2f}s. Expand folders to view contents.")
        self.current_file_label.setText("Ready - Expand folders to explore files")
        self.progress_bar.setValue(100)

    def toggle_reverse_ignore_mode(self, state):
        """Toggle between normal and reverse ignore modes."""
        is_reverse = (state == Qt.CheckState.Checked.value)
        logger.info(f"Toggling reverse ignore mode to: {is_reverse}")
        self.file_tree_widget.reverse_ignore_mode = is_reverse

        # Update all existing items' check states
        root = self.file_tree_widget.invisibleRootItem()
        if root.childCount() > 0:
            self._update_tree_check_states(root.child(0), is_reverse)

    def _update_tree_check_states(self, item, is_reverse):
        """Recursively update check states based on current ignore mode."""
        if item is None:
            return

        # Simple logic:
        # Normal mode (is_reverse=False): Everything starts CHECKED
        # Reverse mode (is_reverse=True): Everything starts UNCHECKED
        # User then manually unchecks (normal) or checks (reverse) what they want

        # Block signals to prevent cascade during bulk update
        tree = item.treeWidget()
        if tree:
            tree.blockSignals(True)

        new_state = Qt.CheckState.Unchecked if is_reverse else Qt.CheckState.Checked
        item.setCheckState(0, new_state)

        logger.debug(f"Updated {item.text(0)} to {new_state}")

        # Recursively update children
        for i in range(item.childCount()):
            child = item.child(i)
            # Skip "Loading..." placeholder
            if child.text(0) != "Loading...":
                self._update_tree_check_states(child, is_reverse)

        # Unblock signals
        if tree:
            tree.blockSignals(False)

    def collect_and_display_extensions(self):
        """Collect file extensions from currently loaded tree items and display as checkboxes."""
        extensions = set()

        # Collect extensions from tree
        def collect_from_item(item):
            if item.text(1) in ["text", "binary"]:  # It's a file
                filename = item.text(0)
                ext = os.path.splitext(filename)[1].lower()
                if ext:
                    extensions.add(ext)

            # Recursively collect from children (only loaded folders)
            for i in range(item.childCount()):
                child = item.child(i)
                if child.text(0) != "Loading...":
                    collect_from_item(child)

        # Start from root
        root = self.file_tree_widget.invisibleRootItem()
        if root.childCount() > 0:
            collect_from_item(root.child(0))

        # Update UI with checkboxes for each extension
        self._update_extension_checkboxes(extensions)

    def _update_extension_checkboxes(self, extensions):
        """Update the extension filter UI with checkboxes for each extension."""
        # Remove existing checkboxes that are no longer present
        for ext in list(self.extension_checkboxes.keys()):
            if ext not in extensions:
                checkbox = self.extension_checkboxes[ext]
                self.extension_checkboxes_layout.removeWidget(checkbox)
                checkbox.deleteLater()
                del self.extension_checkboxes[ext]

        # Add new checkboxes for new extensions
        sorted_extensions = sorted(extensions)
        for ext in sorted_extensions:
            if ext not in self.extension_checkboxes:
                checkbox = QCheckBox(ext)
                checkbox.setChecked(True)  # By default, all extensions are included
                checkbox.stateChanged.connect(lambda state, e=ext: self.toggle_extension_filter(e, state))
                self.extension_checkboxes_layout.addWidget(checkbox)
                self.extension_checkboxes[ext] = checkbox

        # Add stretch at the end
        self.extension_checkboxes_layout.addStretch()

    def toggle_extension_filter(self, extension, state):
        """Toggle filtering for a specific file extension."""
        if state == Qt.CheckState.Checked.value:
            # Include this extension
            self.file_tree_widget.ignored_extensions.discard(extension)
        else:
            # Ignore this extension
            self.file_tree_widget.ignored_extensions.add(extension)

        # Refresh the tree to apply filters (only refresh loaded folders)
        self._refresh_loaded_folders()

    def _refresh_loaded_folders(self):
        """Refresh all loaded folders in the tree to apply extension filters."""
        # Get all loaded directories
        for dir_path in list(self.file_tree_widget.loaded_directories):
            # Find the tree item for this directory
            item = self._find_item_by_path(dir_path)
            if item is not None:
                # Clear children and reload
                item.takeChildren()
                self.file_tree_widget.load_folder_contents(item, dir_path)

        # Update extension list again (some may have been filtered out)
        self.collect_and_display_extensions()

    def _find_item_by_path(self, path):
        """Find a tree item by its filesystem path."""
        def search_item(item, target_path):
            item_path = self.file_tree_widget.get_item_path(item)
            if item_path == target_path:
                return item

            for i in range(item.childCount()):
                child = item.child(i)
                if child.text(0) != "Loading...":
                    result = search_item(child, target_path)
                    if result is not None:
                        return result
            return None

        root = self.file_tree_widget.invisibleRootItem()
        if root.childCount() > 0:
            return search_item(root.child(0), path)
        return None

    @log_performance
    def get_checked_files_from_tree(self):
        """Collect all checked files from the tree, respecting folders and reverse ignore mode."""
        perf_logger.info("Collecting checked files from tree")
        checked_files = []
        reverse_mode = self.file_tree_widget.reverse_ignore_mode
        logger.info(f"Reverse ignore mode: {reverse_mode}")

        def collect_files(item):
            # Skip placeholders
            if item.text(0) == "Loading...":
                return

            item_path = self.file_tree_widget.get_item_path(item)
            is_checked = item.checkState(0) == Qt.CheckState.Checked
            item_type = item.text(1)

            logger.debug(f"Item: {item.text(0)}, Type: {item_type}, Checked: {is_checked}")

            # Handle folders
            if item_type == "folder":
                # In BOTH modes: if folder is checked, we need to look at its children
                # If folder is unchecked, skip it entirely
                if not is_checked:
                    logger.debug(f"Skipping unchecked folder: {item.text(0)}")
                    return

                # Folder is checked - recurse into children
                for i in range(item.childCount()):
                    collect_files(item.child(i))

            # Handle files
            elif item_type in ["text", "binary"]:
                # Only process text files
                if item_type != "text":
                    return

                # Simple logic: if checked, include it (works for both modes)
                if is_checked:
                    logger.debug(f"Adding file: {item_path}")
                    checked_files.append(item_path)
                else:
                    logger.debug(f"Skipping unchecked file: {item.text(0)}")

        # Start from root
        root = self.file_tree_widget.invisibleRootItem()
        if root.childCount() > 0:
            collect_files(root.child(0))

        logger.info(f"Total files collected: {len(checked_files)}")
        return checked_files

    def _collect_files_from_folder(self, folder_path, file_list):
        """Recursively collect all text files from a folder (even if not loaded in tree)."""
        try:
            path = Path(folder_path)
            if not path.exists() or not path.is_dir():
                return

            for item_path in path.iterdir():
                try:
                    if item_path.is_dir():
                        # Recurse into subdirectory
                        self._collect_files_from_folder(str(item_path), file_list)
                    else:
                        # Check if it's a text file
                        extension = item_path.suffix.lower()
                        if extension not in self.file_tree_widget.ignored_extensions:
                            if is_text_file(str(item_path)):
                                file_list.append(str(item_path))
                except Exception as e:
                    print(f"Error collecting file {item_path}: {e}")
                    continue

        except Exception as e:
            print(f"Error collecting from folder {folder_path}: {e}")

    def update_scan_progress(self, current_file, count):
        self.current_file_label.setText(f"Scanning: {current_file}")

        # If count is available, update progress as percentage
        if count > 0:
            self.progress_bar.setMaximum(100)
            progress_value = min(99, int((current_file.count(os.sep) / count) * 100))
            self.progress_bar.setValue(progress_value)

    def add_file_to_tree(self, file_path, file_type, file_size):
        # Called by scan worker for each file found
        if file_type == "text":
            self.file_list.append(file_path)

    def scan_complete(self, file_tree_data, file_counts):
        # Clean up the thread
        self.scan_thread.quit()
        self.scan_thread.wait()

        # Build the tree from the data
        self.build_file_tree(file_tree_data)

        # Update UI
        self.process_btn.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.select_none_btn.setEnabled(True)

        text_count = file_counts["text"]
        binary_count = file_counts["binary"]
        total_count = text_count + binary_count

        self.status_bar.showMessage(f"Found {text_count} text files and {binary_count} binary files")
        self.current_file_label.setText(f"Ready - {text_count} text files available for processing")
        self.progress_bar.setValue(100)

        # Hide loading overlay
        self.loading_overlay.hide_loading()

        # Generate an example output preview
        self.update_output_preview()

    def build_file_tree(self, file_tree_data):
        # Root item
        root_name = os.path.basename(self.input_folder_edit.text())
        root_item = QTreeWidgetItem(self.file_tree_widget, [root_name, "folder", ""])
        root_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        root_item.setFlags(root_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        root_item.setCheckState(0, Qt.CheckState.Checked)

        # Recursively build tree
        self._build_tree_items(root_item, file_tree_data)

        # Expand root
        self.file_tree_widget.expandItem(root_item)

    def _build_tree_items(self, parent_item, items_data):
        # Sort items: folders first, then files
        sorted_items = sorted(items_data.items(), key=lambda x: (not x[1].get("is_dir", False), x[0].lower()))

        for name, data in sorted_items:
            if data.get("is_dir", False):
                # Create folder item
                folder_item = QTreeWidgetItem(parent_item, [name, "folder", ""])
                folder_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
                folder_item.setFlags(folder_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                folder_item.setCheckState(0, Qt.CheckState.Checked)

                # Recursively build children
                self._build_tree_items(folder_item, data.get("children", {}))
            else:
                # Create file item
                file_type = data.get("type", "unknown")
                size_str = self.format_size(data.get("size", 0))

                file_item = QTreeWidgetItem(parent_item, [name, file_type, size_str])

                # Set icon based on file type
                if file_type == "text":
                    file_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
                else:
                    file_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon))

                # Make text files checkable
                if file_type == "text":
                    file_item.setFlags(file_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    file_item.setCheckState(0, Qt.CheckState.Checked)

    def update_exclusion_list(self, item, column):
        """Update the list of excluded files based on checkbox state"""
        if column != 0:
            return

        # Only process if it's a checkbox change
        if not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return

        is_checked = item.checkState(0) == Qt.CheckState.Checked

        # Get the full path of the item
        path_parts = []
        temp_item = item
        while temp_item is not None:
            path_parts.insert(0, temp_item.text(0))
            temp_item = temp_item.parent()

        # Skip the root item name which is just the folder name
        path_parts.pop(0)

        # Get base directory (from the input field)
        base_dir = self.input_folder_edit.text()

        # Construct full path
        full_path = os.path.join(base_dir, *path_parts)

        # Handle directory checkboxes (apply to all children)
        if item.text(1) == "folder":
            self._update_children_check_state(item, is_checked)

            # Update the exclusion list for this directory and all its contents
            if is_checked:
                # Remove this directory and all its contents from exclusion list
                self.excluded_paths = {p for p in self.excluded_paths if not p.startswith(full_path)}
            else:
                # Add all text files in this directory to exclusion list
                self._add_directory_to_exclusions(full_path)
        else:
            # Handle individual file checkboxes
            if is_checked:
                self.excluded_paths.discard(full_path)
            else:
                self.excluded_paths.add(full_path)

        # Update parent folder check state based on children
        self._update_parent_check_state(item.parent())

        # Update the output preview
        self.update_output_preview()

    def update_output_preview(self):
        """Update the output preview tab with sample of how the output will look"""
        if not self.file_list:
            self.output_preview_edit.setPlainText("No files to preview. Scan a folder first.")
            return

        # Get up to 3 non-excluded text files for preview
        preview_files = []
        for file_path in self.file_list:
            if file_path not in self.excluded_paths:
                preview_files.append(file_path)
                if len(preview_files) >= 3:
                    break

        if not preview_files:
            self.output_preview_edit.setPlainText("All files are excluded. Select some files to include in the output.")
            return

        # Generate preview based on selected separator style
        separator_style = self.separator_style_combo.currentText()
        preview_text = f"# Combined Code Preview\n# Using {separator_style} style\n\n"

        for file_path in preview_files:
            rel_path = os.path.relpath(file_path, self.input_folder_edit.text())

            if separator_style == "Simple":
                separator = f"\n\n{'=' * 80}\n"
                header = f"FILE: {rel_path}\n{'=' * 80}\n\n"
                footer = ""
            elif separator_style == "Detailed":
                file_size = os.path.getsize(file_path)
                file_time = os.path.getmtime(file_path)
                timestamp = datetime.fromtimestamp(file_time).strftime('%Y-%m-%d %H:%M:%S')

                separator = f"\n\n{'=' * 80}\n"
                header = f"FILE: {rel_path}\n"
                header += f"SIZE: {file_size} bytes\n"
                header += f"MODIFIED: {timestamp}\n"
                header += f"{'=' * 80}\n\n"
                footer = ""
            else:  # Markdown
                separator = f"\n\n"
                ext = os.path.splitext(file_path)[1][1:] or "text"
                header = f"## {rel_path}\n\n```{ext}\n"
                footer = "\n```\n"

            preview_text += separator
            preview_text += header

            # Add a snippet of the file (first 20 lines)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    content = ''.join(lines[:min(20, len(lines))])
                    if len(lines) > 20:
                        content += "\n... (content truncated for preview) ...\n"
                    preview_text += content
            except Exception as e:
                preview_text += f"[Error reading file: {str(e)}]"

            preview_text += footer

        # Add note about full content
        if len(self.file_list) - len(self.excluded_paths) > 3:
            remaining = len(self.file_list) - len(self.excluded_paths) - 3
            preview_text += f"\n\n... Plus {remaining} more file(s) ...\n"

        self.output_preview_edit.setPlainText(preview_text)

    def _update_children_check_state(self, item, checked):
        """Recursively update all children checkboxes"""
        check_state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked

        # Block signals to prevent cascade
        tree = item.treeWidget()
        if tree:
            tree.blockSignals(True)

        for i in range(item.childCount()):
            child = item.child(i)
            if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                child.setCheckState(0, check_state)

            # Recursively update children of this child if it's a folder
            if child.text(1) == "folder":
                self._update_children_check_state(child, checked)

        # Unblock signals
        if tree:
            tree.blockSignals(False)

    def _update_parent_check_state(self, parent_item):
        """Update parent checkbox based on children state"""
        if parent_item is None:
            return

        all_checked = True
        all_unchecked = True

        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                if child.checkState(0) == Qt.CheckState.Checked:
                    all_unchecked = False
                else:
                    all_checked = False

        # Block signals to prevent cascade when updating parent state
        parent_item.treeWidget().blockSignals(True)
        if all_checked:
            parent_item.setCheckState(0, Qt.CheckState.Checked)
        elif all_unchecked:
            parent_item.setCheckState(0, Qt.CheckState.Unchecked)
        else:
            parent_item.setCheckState(0, Qt.CheckState.PartiallyChecked)
        parent_item.treeWidget().blockSignals(False)

        # Recursively update parent's parent
        self._update_parent_check_state(parent_item.parent())

    def _add_directory_to_exclusions(self, directory):
        """Add all text files from a directory to exclusions list"""
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if is_text_file(file_path):
                    self.excluded_paths.add(file_path)

    def _preview_file(self, file_path):
        """Show file contents in preview tab"""
        try:
            # Update file label
            rel_path = os.path.relpath(file_path, self.input_folder_edit.text())
            self.preview_file_label.setText(f"File: {rel_path}")

            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Set preview content
            self.preview_edit.setPlainText(content)

            # Switch to preview tab
            self.central_widget.findChild(QTabWidget).setCurrentIndex(1)

        except Exception as e:
            self.preview_edit.setPlainText(f"Error loading file: {str(e)}")

    def filter_files(self, filter_text):
        """Filter files in the tree view"""
        if not filter_text:
            # Show all items
            for i in range(self.file_tree_widget.topLevelItemCount()):
                self._show_all_items(self.file_tree_widget.topLevelItem(i))
            return

        filter_text = filter_text.lower()

        # First pass - hide all items
        for i in range(self.file_tree_widget.topLevelItemCount()):
            self._hide_all_items(self.file_tree_widget.topLevelItem(i))

        # Second pass - show matching items and their parents
        for i in range(self.file_tree_widget.topLevelItemCount()):
            self._show_matching_items(self.file_tree_widget.topLevelItem(i), filter_text)

    def _hide_all_items(self, item):
        """Recursively hide all items in the tree"""
        item.setHidden(True)
        for i in range(item.childCount()):
            self._hide_all_items(item.child(i))

    def _show_all_items(self, item):
        """Recursively show all items in the tree"""
        item.setHidden(False)
        for i in range(item.childCount()):
            self._show_all_items(item.child(i))

    def _show_matching_items(self, item, filter_text):
        """Recursively show items that match the filter text"""
        # Check if this item matches
        item_matches = filter_text in item.text(0).lower()

        # Check children
        has_matching_child = False
        for i in range(item.childCount()):
            child_matches = self._show_matching_items(item.child(i), filter_text)
            has_matching_child = has_matching_child or child_matches

        # Show this item if it matches or has a matching child
        show_item = item_matches or has_matching_child
        item.setHidden(not show_item)

        # If this item matches, expand it
        if show_item and item.childCount() > 0:
            self.file_tree_widget.expandItem(item)

        return show_item

    def format_size(self, size_bytes):
        """Format file size in human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    @log_performance
    def start_processing(self, checked=False):
        """Start processing files. The checked parameter is from the button signal and is ignored."""
        input_folder = self.input_folder_edit.text()
        output_file = self.output_file_edit.text()

        logger.info(f"Starting file processing: input={input_folder}, output={output_file}")

        if not input_folder or not os.path.isdir(input_folder):
            logger.warning("Invalid input folder")
            QMessageBox.warning(self, "Invalid Input", "Please select a valid project folder.")
            return

        if not output_file:
            logger.warning("No output file specified")
            QMessageBox.warning(self, "Invalid Output", "Please specify an output file.")
            return

        # Try to create/access the output file path
        try:
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logger.info(f"Created output directory: {output_dir}")
            # Touch the file to see if we can write to it
            open(output_file, 'a').close()
        except Exception as e:
            logger.error(f"Failed to access output file: {e}")
            QMessageBox.critical(self, "Output File Error", f"Unable to access output file: {str(e)}")
            return

        # Get checked files from the tree (respects all filters and ignore modes)
        included_files = self.get_checked_files_from_tree()
        logger.info(f"Collected {len(included_files)} files for processing")
        if not included_files:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file to include in the output.")
            return

        # Show loading overlay
        self.loading_overlay.show_loading(f"Processing {len(included_files)} files...")

        # Set up the worker thread - pass the file list directly
        self.worker_thread = QThread()
        self.worker = FileProcessorWorker(
            input_folder,
            set(),  # No excluded paths - we already filtered with get_checked_files_from_tree
            output_file,
            self.separator_style_combo.currentText(),
            included_files  # Pass the specific list of files to process
        )
        self.worker.moveToThread(self.worker_thread)

        # Connect signals
        self.worker_thread.started.connect(self.worker.process_files)
        self.worker.progress.connect(self.update_progress)
        self.worker.current_file.connect(self.update_current_file)
        self.worker.processing_complete.connect(self.processing_finished)

        # Update UI
        self.process_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.status_bar.showMessage(f"Processing {len(included_files)} files...")

        # Start processing
        self.worker_thread.start()

    def cancel_processing(self, checked=False):
        """Cancel file processing. The checked parameter is from the signal and is ignored."""
        if self.worker:
            self.worker.cancel()
        self.status_bar.showMessage("Cancelling...")

    def update_progress(self, current, total):
        if total == 0:
            self.progress_bar.setValue(0)
        else:
            progress_percent = int((current / total) * 100)
            self.progress_bar.setValue(progress_percent)
            self.status_bar.showMessage(f"Processing: {current}/{total} files")

    def update_current_file(self, file_path):
        self.current_file_label.setText(f"Processing: {file_path}")

    def processing_finished(self, success, message):
        # Clean up thread
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()

        # Hide loading overlay
        self.loading_overlay.hide_loading()

        # Update UI
        self.process_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.current_file_label.setText(message)
        self.status_bar.showMessage(message)

        if success:
            # Add success animation
            self.progress_bar.setValue(100)

            # Show success message with dialog
            QMessageBox.information(self, "Processing Complete", message)

            # Offer to open the output file
            reply = QMessageBox.question(
                self, "Open File",
                "Would you like to preview the generated file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                try:
                    with open(self.output_file_edit.text(), 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Update the preview tab with content
                    self.preview_file_label.setText(f"Output File: {os.path.basename(self.output_file_edit.text())}")
                    self.preview_edit.setPlainText(content)
                    self.central_widget.findChild(QTabWidget).setCurrentIndex(1)

                except Exception as e:
                    QMessageBox.warning(self, "Preview Error", f"Could not load file preview: {str(e)}")
        else:
            # Show error message
            QMessageBox.warning(self, "Processing Error", message)

    def select_all_files(self, checked=False):
        """Select all files in the tree. The checked parameter is from the signal and is ignored."""
        root_item = self.file_tree_widget.topLevelItem(0)
        if root_item:
            # Block signals during bulk operation
            self.file_tree_widget.blockSignals(True)
            root_item.setCheckState(0, Qt.CheckState.Checked)
            self._update_children_check_state(root_item, True)
            self.file_tree_widget.blockSignals(False)

            self.excluded_paths.clear()

            # Update the output preview
            self.update_output_preview()

            # Show confirmation message
            self.status_bar.showTemporaryMessage("Selected all files")

    def deselect_all_files(self, checked=False):
        """Deselect all files in the tree. The checked parameter is from the signal and is ignored."""
        root_item = self.file_tree_widget.topLevelItem(0)
        if root_item:
            # Block signals during bulk operation
            self.file_tree_widget.blockSignals(True)
            root_item.setCheckState(0, Qt.CheckState.Unchecked)
            self._update_children_check_state(root_item, False)
            self.file_tree_widget.blockSignals(False)

            # Add all files to excluded paths
            input_folder = self.input_folder_edit.text()
            if os.path.isdir(input_folder):
                self._add_directory_to_exclusions(input_folder)

            # Update the output preview
            self.update_output_preview()

            # Show confirmation message
            self.status_bar.showTemporaryMessage("Deselected all files")

    def show_about_dialog(self, checked=False):
        """Show about dialog. The checked parameter is from the signal and is ignored."""
        about_text = """
        <div style="text-align: center;">
            <h2 style="color: #007aff;">Code Combiner</h2>
            <p style="font-size: 14px;">Version 2.0</p>
            <p>A powerful utility for combining multiple code files into a single text file,
            preserving file structures and adding clear separators.</p>
            <p>Perfect for AI analysis, code reviews, and documentation.</p>
            <p style="margin-top: 20px;">Features: Lazy Loading, Parallel Processing, Performance Logging</p>
            <p>Created with PyQt6</p>
        </div>
        """
        QMessageBox.about(self, "About Code Combiner", about_text)

    def closeEvent(self, event):
        # Save settings on exit
        self.save_settings()

        # Cancel any running operations
        if self.worker and self.worker_thread and self.worker_thread.isRunning():
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "A file processing operation is still running. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.worker.cancel()
                self.worker_thread.quit()
                self.worker_thread.wait()
            else:
                event.ignore()
                return

        event.accept()


# Application entry point
def main():
    # Initialize MIME types database
    mimetypes.init()

    # Set application metadata
    app.setApplicationName("Code Combiner")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("CodeCombiner")

    # Create and show the main window
    window = CodeCombinerApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()