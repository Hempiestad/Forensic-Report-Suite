"""
Diagnostics Module - System Configuration Detection & Reporting
Captures system state for troubleshooting cross-workstation issues
"""

import os
import sys
import json
import logging
import platform
import psutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SystemDiagnostics:
    """Comprehensive system diagnostics for troubleshooting."""
    
    def __init__(self):
        self.diagnostics = {}
        self.timestamp = datetime.now().isoformat()
    
    def gather_all(self):
        """Collect all diagnostic information."""
        self.diagnostics = {
            'timestamp': self.timestamp,
            'system': self.get_system_info(),
            'python': self.get_python_info(),
            'dependencies': self.get_dependencies(),
            'filesystem': self.get_filesystem_info(),
            'database': self.get_database_info(),
            'display': self.get_display_info(),
            'performance': self.get_performance_baseline(),
        }
        return self.diagnostics
    
    def get_system_info(self):
        """Gather OS and hardware information."""
        try:
            return {
                'os': platform.system(),
                'os_version': platform.version(),
                'os_release': platform.release(),
                'architecture': platform.machine(),
                'cpu_count': psutil.cpu_count(logical=True),
                'cpu_count_physical': psutil.cpu_count(logical=False),
                'cpu_freq_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else None,
                'ram_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                'ram_available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
                'ram_percent_used': psutil.virtual_memory().percent,
                'disk_free_gb': round(psutil.disk_usage('/').free / (1024**3), 2) if os.path.exists('/') else None,
            }
        except Exception as e:
            logger.error(f"Failed to gather system info: {e}")
            return {'error': str(e)}
    
    def get_python_info(self):
        """Gather Python runtime information."""
        try:
            return {
                'version': platform.python_version(),
                'implementation': platform.python_implementation(),
                'compiler': platform.python_compiler(),
                'executable': sys.executable,
                'prefix': sys.prefix,
                'base_prefix': sys.base_prefix,
                'virtual_env_active': hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix),
            }
        except Exception as e:
            logger.error(f"Failed to gather Python info: {e}")
            return {'error': str(e)}
    
    def get_dependencies(self):
        """Check critical dependencies."""
        critical = ['PyQt5', 'sqlalchemy', 'weasyprint', 'pandas', 'openpyxl']
        optional = ['matplotlib', 'numpy', 'pillow', 'argon2']
        
        deps = {'critical': {}, 'optional': {}}
        
        for pkg_name in critical:
            try:
                pkg = __import__(pkg_name)
                version = getattr(pkg, '__version__', 'unknown')
                deps['critical'][pkg_name] = {'status': 'installed', 'version': version}
            except ImportError:
                deps['critical'][pkg_name] = {'status': 'missing', 'version': None}
        
        for pkg_name in optional:
            try:
                pkg = __import__(pkg_name)
                version = getattr(pkg, '__version__', 'unknown')
                deps['optional'][pkg_name] = {'status': 'installed', 'version': version}
            except ImportError:
                deps['optional'][pkg_name] = {'status': 'missing', 'version': None}
        
        return deps
    
    def get_filesystem_info(self):
        """Check file system access and permissions."""
        try:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            return {
                'app_directory': app_dir,
                'app_dir_writable': os.access(app_dir, os.W_OK),
                'temp_dir': os.environ.get('TEMP', 'N/A'),
                'temp_dir_writable': os.access(os.environ.get('TEMP', ''), os.W_OK) if 'TEMP' in os.environ else None,
                'appdata_dir': os.environ.get('APPDATA', 'N/A'),
                'documents_dir': str(Path.home() / 'Documents'),
                'documents_writable': os.access(str(Path.home() / 'Documents'), os.W_OK),
            }
        except Exception as e:
            logger.error(f"Failed to gather filesystem info: {e}")
            return {'error': str(e)}
    
    def get_database_info(self):
        """Check database configuration and accessibility."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            db_info = {'config_exists': os.path.exists(config_path)}
            
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        db_info['db_type'] = config.get('database_type', 'unknown')
                        db_info['database_name'] = config.get('database_name', 'unknown')
                except Exception as e:
                    db_info['config_read_error'] = str(e)
            
            # Check database file existence
            db_path = os.path.join(os.path.dirname(__file__), 'forensic_cases.db')
            db_info['database_exists'] = os.path.exists(db_path)
            if os.path.exists(db_path):
                db_info['database_size_mb'] = round(os.path.getsize(db_path) / (1024**2), 2)
                db_info['database_writable'] = os.access(db_path, os.W_OK)
            
            return db_info
        except Exception as e:
            logger.error(f"Failed to gather database info: {e}")
            return {'error': str(e)}
    
    def get_display_info(self):
        """Gather display configuration (requires PyQt5)."""
        try:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtGui import QScreen
            
            # Check if QApplication exists
            app = QApplication.instance()
            if not app:
                return {'status': 'QApplication not initialized'}
            
            display_info = {}
            screens = app.screens()
            display_info['screen_count'] = len(screens)
            display_info['screens'] = []
            
            for i, screen in enumerate(screens):
                screen_data = {
                    'index': i,
                    'name': screen.name(),
                    'geometry': str(screen.geometry()),
                    'available_geometry': str(screen.availableGeometry()),
                    'dpi': screen.logicalDotsPerInch(),
                    'physical_dpi': screen.physicalDotsPerInch(),
                    'size_mm': f"{screen.physicalSize().width():.0f}x{screen.physicalSize().height():.0f}",
                    'scale_factor': screen.devicePixelRatio(),
                }
                display_info['screens'].append(screen_data)
            
            return display_info
        except Exception as e:
            logger.warning(f"Failed to gather display info (expected if QApplication not initialized): {e}")
            return {'status': 'Not available', 'error': str(e)}
    
    def get_performance_baseline(self):
        """Capture current performance metrics."""
        try:
            process = psutil.Process()
            return {
                'memory_rss_mb': round(process.memory_info().rss / (1024**2), 2),
                'memory_vms_mb': round(process.memory_info().vms / (1024**2), 2),
                'memory_percent': process.memory_percent(),
                'cpu_count': psutil.cpu_count(),
                'cpu_percent': psutil.cpu_percent(interval=0.1),
            }
        except Exception as e:
            logger.error(f"Failed to gather performance info: {e}")
            return {'error': str(e)}
    
    def to_json(self):
        """Export diagnostics as JSON string."""
        return json.dumps(self.diagnostics, indent=2, default=str)
    
    def to_dict(self):
        """Return diagnostics as dictionary."""
        return self.diagnostics
    
    def save_to_file(self, filepath=None):
        """Save diagnostics to a file."""
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(__file__),
                f"diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
        
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(self.to_json())
            logger.info(f"Diagnostics saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save diagnostics: {e}")
            return None
    
    def log_diagnostics(self):
        """Log all diagnostics at INFO level."""
        logger.info("=== SYSTEM DIAGNOSTICS ===")
        for section, data in self.diagnostics.items():
            logger.info(f"\n[{section.upper()}]")
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, (list, dict)):
                        logger.info(f"  {key}: {json.dumps(value, indent=4, default=str)}")
                    else:
                        logger.info(f"  {key}: {value}")
            else:
                logger.info(f"  {data}")
        logger.info("=== END DIAGNOSTICS ===")


def validate_dependencies():
    """Validate that all critical dependencies are available."""
    required = ['PyQt5', 'sqlalchemy', 'weasyprint', 'pandas']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        return False, f"Missing critical dependencies: {', '.join(missing)}"
    
    return True, "All dependencies available"


def detect_safe_mode():
    """Detect if application should run in safe mode."""
    # Check for --safe-mode command-line flag
    return '--safe-mode' in sys.argv


if __name__ == '__main__':
    # Allow running as: python diagnostics.py
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    diag = SystemDiagnostics()
    diag.gather_all()
    diag.log_diagnostics()
    
    output_file = diag.save_to_file()
    if output_file:
        print(f"\n✓ Diagnostics saved to: {output_file}")
    
    # Exit with error code if critical dependencies missing
    valid, msg = validate_dependencies()
    print(f"\nDependency check: {msg}")
    sys.exit(0 if valid else 1)
