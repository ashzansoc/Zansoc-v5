"""Debug utilities for ZanSoc CLI troubleshooting."""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Any
from .utils.logger import get_logger


class DebugCollector:
    """Collects comprehensive debug information for troubleshooting."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.debug_info = {}
    
    def collect_system_info(self) -> Dict[str, Any]:
        """Collect system information."""
        try:
            info = {
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': sys.version,
                'python_executable': sys.executable,
                'python_path': sys.path,
            }
            
            # Add environment variables
            info['environment'] = {
                'PATH': os.environ.get('PATH', ''),
                'PYTHONPATH': os.environ.get('PYTHONPATH', ''),
                'HOME': os.environ.get('HOME', ''),
                'USER': os.environ.get('USER', ''),
            }
            
            return info
        except Exception as e:
            self.logger.error(f"Failed to collect system info: {e}")
            return {'error': str(e)}
    
    def collect_python_packages(self) -> Dict[str, Any]:
        """Collect installed Python packages."""
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'list', '--format=json'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                packages = json.loads(result.stdout)
                return {
                    'packages': packages,
                    'total_count': len(packages)
                }
            else:
                return {'error': result.stderr}
        except Exception as e:
            self.logger.error(f"Failed to collect package info: {e}")
            return {'error': str(e)}
    
    def test_ray_import(self) -> Dict[str, Any]:
        """Test Ray import with detailed diagnostics."""
        try:
            # Test basic import
            import_test = subprocess.run([
                sys.executable, '-c', 'import ray; print("SUCCESS")'
            ], capture_output=True, text=True, timeout=10)
            
            result = {
                'import_success': import_test.returncode == 0,
                'stdout': import_test.stdout,
                'stderr': import_test.stderr,
                'return_code': import_test.returncode
            }
            
            if import_test.returncode == 0:
                # Get Ray version
                version_test = subprocess.run([
                    sys.executable, '-c', 'import ray; print(ray.__version__)'
                ], capture_output=True, text=True, timeout=10)
                
                if version_test.returncode == 0:
                    result['ray_version'] = version_test.stdout.strip()
            
            return result
        except subprocess.TimeoutExpired:
            return {'error': 'Ray import timed out (>10s)', 'timeout': True}
        except Exception as e:
            return {'error': str(e)}
    
    def collect_zansoc_info(self) -> Dict[str, Any]:
        """Collect ZanSoc-specific information."""
        try:
            zansoc_dir = Path.home() / '.zansoc'
            info = {
                'zansoc_dir_exists': zansoc_dir.exists(),
                'zansoc_dir_path': str(zansoc_dir)
            }
            
            if zansoc_dir.exists():
                info['contents'] = [str(p) for p in zansoc_dir.iterdir()]
                
                # Check for specific files
                important_files = ['zansoc', 'venv', 'Zansoc-v5', '.user_mode']
                for file in important_files:
                    file_path = zansoc_dir / file
                    info[f'{file}_exists'] = file_path.exists()
                    if file_path.exists():
                        if file_path.is_file():
                            info[f'{file}_size'] = file_path.stat().st_size
                        elif file_path.is_dir():
                            info[f'{file}_contents'] = len(list(file_path.iterdir()))
            
            return info
        except Exception as e:
            return {'error': str(e)}
    
    def generate_debug_report(self) -> str:
        """Generate comprehensive debug report."""
        self.logger.info("Generating debug report...")
        
        report = {
            'system_info': self.collect_system_info(),
            'python_packages': self.collect_python_packages(),
            'ray_diagnostics': self.test_ray_import(),
            'zansoc_info': self.collect_zansoc_info()
        }
        
        # Format as readable text
        output = []
        output.append("=" * 80)
        output.append("ZANSOC DEBUG REPORT")
        output.append("=" * 80)
        
        for section, data in report.items():
            output.append(f"\n[{section.upper()}]")
            output.append("-" * 40)
            self._format_dict(data, output, indent=0)
        
        return "\n".join(output)
    
    def _format_dict(self, data: Any, output: List[str], indent: int = 0):
        """Format dictionary data for readable output."""
        prefix = "  " * indent
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    output.append(f"{prefix}{key}:")
                    self._format_dict(value, output, indent + 1)
                else:
                    output.append(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    output.append(f"{prefix}[{i}]:")
                    self._format_dict(item, output, indent + 1)
                else:
                    output.append(f"{prefix}[{i}]: {item}")
        else:
            output.append(f"{prefix}{data}")


def create_debug_report() -> str:
    """Create and return a debug report."""
    collector = DebugCollector()
    return collector.generate_debug_report()


def save_debug_report(filepath: str = None) -> str:
    """Save debug report to file."""
    if filepath is None:
        filepath = Path.home() / '.zansoc' / 'debug_report.txt'
    
    report = create_debug_report()
    
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(report)
    
    return str(filepath)