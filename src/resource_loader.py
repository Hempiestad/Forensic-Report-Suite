"""
Resource Loader Module - Robust Asset Loading with Fallback Chain
Handles resource loading in both development and compiled (PyInstaller) environments
"""

import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ResourceLoader:
    """Handles resource loading with multiple fallback strategies."""
    
    @staticmethod
    def get_base_path():
        """Get the base application path (handles PyInstaller compiled mode)."""
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle
            return sys._MEIPASS
        else:
            # Running in development — this file lives in src/, so root is one level up
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    @staticmethod
    def resource_path(relative_path):
        """
        Get full path to a resource file.
        Works in both development and compiled modes.
        
        Args:
            relative_path: Path relative to application root
            
        Returns:
            Full path to resource file
        """
        base_path = ResourceLoader.get_base_path()
        return os.path.join(base_path, relative_path)
    
    @staticmethod
    def load_file(relative_path, mode='r', encoding='utf-8'):
        """
        Load a file with logging.
        
        Args:
            relative_path: Path relative to application root
            mode: File open mode ('r', 'rb', etc.)
            encoding: Text encoding (if applicable)
            
        Returns:
            File content or None if load fails
        """
        try:
            full_path = ResourceLoader.resource_path(relative_path)
            
            if not os.path.exists(full_path):
                logger.warning(f"Resource file not found: {relative_path} (checked: {full_path})")
                return None
            
            if 'b' in mode:
                with open(full_path, mode) as f:
                    content = f.read()
            else:
                with open(full_path, mode, encoding=encoding) as f:
                    content = f.read()
            
            logger.debug(f"Loaded resource: {relative_path}")
            return content
        
        except Exception as e:
            logger.error(f"Failed to load resource '{relative_path}': {e}")
            return None
    
    @staticmethod
    def load_image(relative_path, fallback_text=None, fallback_color='#CCCCCC', min_width=200):
        """
        Load an image and return QPixmap with fallback to text label.
        
        Args:
            relative_path: Path to image file relative to app root
            fallback_text: Text to display if image fails to load
            fallback_color: Background color for fallback label
            min_width: Minimum width for fallback label
            
        Returns:
            (pixmap, loaded_successfully) tuple
            If load fails, returns (None, False) for caller to create fallback widget
        """
        try:
            from PyQt5.QtGui import QPixmap
            
            full_path = ResourceLoader.resource_path(relative_path)
            
            if not os.path.exists(full_path):
                logger.warning(f"Image resource not found: {relative_path}")
                return None, False
            
            pixmap = QPixmap(full_path)
            
            if pixmap.isNull():
                logger.warning(f"Failed to load image as pixmap: {relative_path}")
                return None, False
            
            logger.debug(f"Loaded image: {relative_path}")
            return pixmap, True
        
        except Exception as e:
            logger.error(f"Exception loading image '{relative_path}': {e}")
            return None, False
    
    @staticmethod
    def load_json(relative_path, default=None):
        """
        Load JSON file with fallback to default value.
        
        Args:
            relative_path: Path to JSON file
            default: Default value if load fails
            
        Returns:
            Parsed JSON or default value
        """
        import json
        
        try:
            content = ResourceLoader.load_file(relative_path, mode='r')
            if content is None:
                logger.warning(f"Using default value for JSON: {relative_path}")
                return default
            
            return json.loads(content)
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in '{relative_path}': {e}")
            return default
        except Exception as e:
            logger.error(f"Failed to load JSON '{relative_path}': {e}")
            return default
    
    @staticmethod
    def find_file(filename, search_paths=None):
        """
        Search for a file in multiple locations.
        
        Args:
            filename: Name of file to find
            search_paths: List of paths to search (relative to app root).
                         Defaults to common locations.
            
        Returns:
            Full path if found, None otherwise
        """
        if search_paths is None:
            search_paths = [
                '.',
                'resources',
                'assets',
                'images',
                os.path.expanduser('~/Documents'),
                os.path.expanduser('~/Downloads'),
            ]
        
        base_path = ResourceLoader.get_base_path()
        
        for search_dir in search_paths:
            if os.path.isabs(search_dir):
                check_path = os.path.join(search_dir, filename)
            else:
                check_path = os.path.join(base_path, search_dir, filename)
            
            if os.path.exists(check_path):
                logger.debug(f"Found file: {filename} at {check_path}")
                return check_path
        
        logger.warning(f"File not found in any search path: {filename}")
        return None
    
    @staticmethod
    def ensure_directory(relative_path):
        """
        Ensure directory exists, creating if necessary.
        
        Args:
            relative_path: Directory path relative to app root
            
        Returns:
            Full path to directory, or None if creation fails
        """
        try:
            full_path = ResourceLoader.resource_path(relative_path)
            os.makedirs(full_path, exist_ok=True)
            logger.debug(f"Directory available: {relative_path}")
            return full_path
        except Exception as e:
            logger.error(f"Failed to create directory '{relative_path}': {e}")
            return None
    
    @staticmethod
    def get_size_readable(filepath):
        """Get file size in human-readable format."""
        if not os.path.exists(filepath):
            return "N/A"
        
        size = os.path.getsize(filepath)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        
        return f"{size:.1f} TB"
    
    @staticmethod
    def validate_bundle():
        """
        Validate that critical resources are available.
        Called at startup to detect packaging issues.
        
        Returns:
            (all_valid, messages) tuple
        """
        critical_files = [
            'config.json',
            'logging_config.py',
        ]
        
        messages = []
        all_valid = True
        
        for filename in critical_files:
            path = ResourceLoader.resource_path(filename)
            if os.path.exists(path):
                messages.append(f"✓ {filename}")
            else:
                messages.append(f"✗ {filename} (MISSING)")
                all_valid = False
        
        if all_valid:
            logger.info("Resource bundle validation: PASS")
        else:
            logger.warning("Resource bundle validation: FAIL - some files missing")
        
        return all_valid, messages


# Global instance for easy access
_loader = ResourceLoader()

# Convenience functions
def resource_path(relative_path):
    """Shorthand for ResourceLoader.resource_path()"""
    return _loader.resource_path(relative_path)


def load_file(relative_path, mode='r', encoding='utf-8'):
    """Shorthand for ResourceLoader.load_file()"""
    return _loader.load_file(relative_path, mode, encoding)


def load_image(relative_path, fallback_text=None):
    """Shorthand for ResourceLoader.load_image()"""
    return _loader.load_image(relative_path, fallback_text)


def load_json(relative_path, default=None):
    """Shorthand for ResourceLoader.load_json()"""
    return _loader.load_json(relative_path, default)


if __name__ == '__main__':
    # Test resource loader
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print(f"Base path: {ResourceLoader.get_base_path()}")
    print(f"Testing resource loading...\n")
    
    # Validate bundle
    valid, messages = ResourceLoader.validate_bundle()
    for msg in messages:
        print(msg)
    
    print(f"\nBundle validation: {'PASS' if valid else 'FAIL'}")
