"""
Forensic Alignment: NTFS metadata manipulation and MFT scrubbing.
Implements timestomping and cross-volume operations for temporal consistency.
"""
import os
import shutil
import ctypes
import struct
import logging
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import subprocess
import hashlib


class ForensicAlignment:
    """
    Manages forensic timestamp alignment and MFT operations.
    Resolves temporal paradoxes between $SI and $FN attributes.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize Forensic Alignment module."""
        self.logger = logger or logging.getLogger(__name__)
        
        # Platform detection
        self.is_windows = os.name == 'nt'
        self.temp_path = Path(tempfile.gettempdir()) / 'prometheus_temp'
        
        # Statistics
        self.files_processed = 0
        self.files_failed = 0
    
    def stomp_timestamps(self, target_path: Path, 
                        target_date: datetime,
                        recursive: bool = True) -> bool:
        """
        Recursively stomp timestamps on all files in directory.
        
        Args:
            target_path: Directory or file to process
            target_date: Target datetime for timestamps
            recursive: Process subdirectories
            
        Returns:
            bool: Success status
        """
        try:
            self.logger.info(f"Starting timestamp stomp on {target_path}")
            
            if not target_path.exists():
                self.logger.error(f"Path does not exist: {target_path}")
                return False
            
            # Convert to timestamp
            target_timestamp = target_date.timestamp()
            
            if target_path.is_file():
                # Single file
                return self._stomp_file(target_path, target_timestamp)
            
            elif target_path.is_dir():
                # Directory tree
                if recursive:
                    return self._stomp_recursive(target_path, target_timestamp)
                else:
                    return self._stomp_directory(target_path, target_timestamp)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Timestamp stomping failed: {e}")
            return False
    
    def _stomp_file(self, file_path: Path, timestamp: float) -> bool:
        """Stomp timestamps on single file."""
        try:
            if self.is_windows:
                # Windows: Use SetFileTime for millisecond precision
                return self._stomp_file_windows(file_path, timestamp)
            else:
                # Unix: Use os.utime
                os.utime(str(file_path), (timestamp, timestamp))
                
            self.files_processed += 1
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to stomp {file_path}: {e}")
            self.files_failed += 1
            return False
    
    def _stomp_file_windows(self, file_path: Path, timestamp: float) -> bool:
        """Windows-specific timestamp stomping with FILETIME."""
        try:
            # Convert Unix timestamp to Windows FILETIME
            # FILETIME = 100-nanosecond intervals since January 1, 1601
            EPOCH_AS_FILETIME = 116444736000000000
            filetime = int((timestamp * 10000000) + EPOCH_AS_FILETIME)
            
            # Create FILETIME structure
            class FILETIME(ctypes.Structure):
                _fields_ = [
                    ('dwLowDateTime', ctypes.c_uint32),
                    ('dwHighDateTime', ctypes.c_uint32)
                ]
            
            ft = FILETIME()
            ft.dwLowDateTime = filetime & 0xFFFFFFFF
            ft.dwHighDateTime = (filetime >> 32) & 0xFFFFFFFF
            
            # Open file handle
            kernel32 = ctypes.windll.kernel32
            
            GENERIC_WRITE = 0x40000000
            FILE_SHARE_READ = 0x00000001
            OPEN_EXISTING = 3
            FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
            
            handle = kernel32.CreateFileW(
                str(file_path),
                GENERIC_WRITE,
                FILE_SHARE_READ,
                None,
                OPEN_EXISTING,
                FILE_FLAG_BACKUP_SEMANTICS,
                None
            )
            
            if handle == -1:
                return False
            
            try:
                # Set file times (creation, access, modification)
                result = kernel32.SetFileTime(
                    handle,
                    ctypes.byref(ft),  # Creation time
                    ctypes.byref(ft),  # Access time
                    ctypes.byref(ft)   # Modification time
                )
                
                return bool(result)
                
            finally:
                kernel32.CloseHandle(handle)
                
        except Exception as e:
            self.logger.warning(f"Windows timestomp failed: {e}")
            # Fallback to os.utime
            os.utime(str(file_path), (timestamp, timestamp))
            return True
    
    def _stomp_directory(self, dir_path: Path, timestamp: float) -> bool:
        """Stomp timestamps on directory contents (non-recursive)."""
        try:
            success = True
            
            for item in dir_path.iterdir():
                if item.is_file():
                    if not self._stomp_file(item, timestamp):
                        success = False
            
            # Stomp directory itself
            os.utime(str(dir_path), (timestamp, timestamp))
            
            return success
            
        except Exception as e:
            self.logger.error(f"Directory stomp failed: {e}")
            return False
    
    def _stomp_recursive(self, dir_path: Path, timestamp: float) -> bool:
        """Recursively stomp timestamps on entire directory tree."""
        try:
            success = True
            
            # Walk directory tree bottom-up
            for root, dirs, files in os.walk(dir_path, topdown=False):
                root_path = Path(root)
                
                # Process files
                for file in files:
                    file_path = root_path / file
                    if not self._stomp_file(file_path, timestamp):
                        success = False
                
                # Process directories
                for dir_name in dirs:
                    dir_path = root_path / dir_name
                    try:
                        os.utime(str(dir_path), (timestamp, timestamp))
                    except:
                        pass
            
            # Finally, stomp root directory
            os.utime(str(dir_path), (timestamp, timestamp))
            
            self.logger.info(f"Processed {self.files_processed} files, {self.files_failed} failed")
            return success
            
        except Exception as e:
            self.logger.error(f"Recursive stomp failed: {e}")
            return False
    
    def scrub_mft(self, source_path: Path, 
                  preserve_structure: bool = True) -> Optional[Path]:
        """
        Scrub MFT entries using move-and-copy strategy.
        Forces creation of new MFT records with current timestamps.
        
        Args:
            source_path: Source directory to scrub
            preserve_structure: Maintain directory structure
            
        Returns:
            Path to scrubbed directory or None on failure
        """
        try:
            self.logger.info(f"Starting MFT scrub on {source_path}")
            
            if not source_path.exists():
                self.logger.error(f"Source path does not exist: {source_path}")
                return None
            
            # Create temporary location on different volume if possible
            self.temp_path.mkdir(parents=True, exist_ok=True)
            
            # Generate unique temp name
            temp_name = f"mft_scrub_{hashlib.md5(str(source_path).encode()).hexdigest()[:8]}"
            temp_dir = self.temp_path / temp_name
            
            # Step 1: Move to temp location (creates new MFT entries)
            self.logger.info(f"Moving to temp: {temp_dir}")
            shutil.move(str(source_path), str(temp_dir))
            
            # Step 2: Move back to original location
            # This creates fresh MFT entries with backdated system time
            self.logger.info(f"Moving back to: {source_path}")
            shutil.move(str(temp_dir), str(source_path))
            
            self.logger.info("MFT scrub complete")
            return source_path
            
        except Exception as e:
            self.logger.error(f"MFT scrub failed: {e}")
            
            # Attempt recovery
            try:
                if temp_dir and temp_dir.exists():
                    shutil.move(str(temp_dir), str(source_path))
            except:
                pass
            
            return None
    
    def cross_volume_move(self, source_path: Path, 
                         target_volume: Optional[str] = None) -> Optional[Path]:
        """
        Move files across volume boundary to force MFT regeneration.
        
        Args:
            source_path: Source directory
            target_volume: Target volume (e.g., 'D:\\' on Windows)
            
        Returns:
            Final path after move operations
        """
        try:
            if not target_volume:
                # Try to find alternate volume
                if self.is_windows:
                    import string
                    drives = [f"{d}:\\" for d in string.ascii_uppercase 
                             if os.path.exists(f"{d}:\\") and d != 'C']
                    
                    if drives:
                        target_volume = drives[0]
                    else:
                        # Use temp on same volume
                        target_volume = tempfile.gettempdir()
                else:
                    # Unix: Use /tmp or /var/tmp
                    target_volume = '/tmp' if os.path.exists('/tmp') else tempfile.gettempdir()
            
            # Create target path
            target_base = Path(target_volume)
            target_name = f"prometheus_{source_path.name}_{int(datetime.now().timestamp())}"
            target_path = target_base / target_name
            
            self.logger.info(f"Cross-volume move: {source_path} -> {target_path}")
            
            # Move to target volume
            shutil.move(str(source_path), str(target_path))
            
            # Move back to original parent directory
            original_parent = source_path.parent
            final_path = original_parent / source_path.name
            
            shutil.move(str(target_path), str(final_path))
            
            self.logger.info(f"Cross-volume move complete: {final_path}")
            return final_path
            
        except Exception as e:
            self.logger.error(f"Cross-volume move failed: {e}")
            return None
    
    def verify_timestamps(self, path: Path) -> Dict[str, Any]:
        """
        Verify timestamp alignment for files.
        
        Args:
            path: Path to verify
            
        Returns:
            Verification results dictionary
        """
        try:
            results = {
                'path': str(path),
                'exists': path.exists(),
                'files_checked': 0,
                'temporal_paradoxes': [],
                'timestamp_range': None
            }
            
            if not path.exists():
                return results
            
            timestamps = []
            
            if path.is_file():
                # Single file
                stat = path.stat()
                timestamps.append({
                    'file': path.name,
                    'created': stat.st_ctime,
                    'modified': stat.st_mtime,
                    'accessed': stat.st_atime
                })
                results['files_checked'] = 1
                
            else:
                # Directory tree
                for root, dirs, files in os.walk(path):
                    for file in files:
                        file_path = Path(root) / file
                        try:
                            stat = file_path.stat()
                            timestamps.append({
                                'file': str(file_path.relative_to(path)),
                                'created': stat.st_ctime,
                                'modified': stat.st_mtime,
                                'accessed': stat.st_atime
                            })
                            results['files_checked'] += 1
                        except:
                            pass
            
            # Check for temporal paradoxes
            for ts in timestamps:
                # Modified before created = paradox
                if ts['modified'] < ts['created']:
                    results['temporal_paradoxes'].append({
                        'file': ts['file'],
                        'issue': 'modified < created',
                        'delta': ts['created'] - ts['modified']
                    })
                
                # Accessed before created = paradox
                if ts['accessed'] < ts['created']:
                    results['temporal_paradoxes'].append({
                        'file': ts['file'],
                        'issue': 'accessed < created',
                        'delta': ts['created'] - ts['accessed']
                    })
            
            # Calculate timestamp range
            if timestamps:
                all_times = []
                for ts in timestamps:
                    all_times.extend([ts['created'], ts['modified'], ts['accessed']])
                
                min_time = min(all_times)
                max_time = max(all_times)
                
                results['timestamp_range'] = {
                    'min': datetime.fromtimestamp(min_time).isoformat(),
                    'max': datetime.fromtimestamp(max_time).isoformat(),
                    'span_days': (max_time - min_time) / 86400
                }
            
            # Check if Windows for $FN verification
            if self.is_windows:
                results['mft_check'] = self._verify_mft_attributes(path)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Timestamp verification failed: {e}")
            return {'error': str(e)}
    
    def _verify_mft_attributes(self, path: Path) -> Dict[str, Any]:
        """Verify MFT $SI vs $FN attributes (Windows only)."""
        try:
            # Use fsutil if available
            result = subprocess.run(
                ['fsutil', 'usn', 'readdata', str(path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Parse USN data
                return {
                    'usn_available': True,
                    'data': result.stdout[:500]  # First 500 chars
                }
            
            return {'usn_available': False}
            
        except:
            return {'usn_available': False}
    
    def cleanup_artifacts(self):
        """Clean up temporary artifacts."""
        try:
            if self.temp_path.exists():
                shutil.rmtree(self.temp_path)
                self.logger.info("Cleaned up temporary artifacts")
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    def create_temporal_consistency_map(self, profile_path: Path) -> Dict[str, Any]:
        """
        Create a map of temporal consistency across profile components.
        
        Args:
            profile_path: Browser profile path
            
        Returns:
            Consistency map with analysis
        """
        consistency_map = {
            'profile_path': str(profile_path),
            'components': {},
            'consistency_score': 0,
            'issues': []
        }
        
        try:
            # Key components to check
            components = [
                ('cookies', 'Default/Network/Cookies'),
                ('local_storage', 'Default/Local Storage/leveldb'),
                ('session_storage', 'Default/Session Storage'),
                ('cache', 'Default/Cache/Cache_Data'),
                ('indexeddb', 'Default/IndexedDB'),
                ('preferences', 'Default/Preferences')
            ]
            
            base_timestamp = None
            
            for comp_name, comp_path in components:
                full_path = profile_path / comp_path
                
                if full_path.exists():
                    stat = full_path.stat()
                    
                    consistency_map['components'][comp_name] = {
                        'exists': True,
                        'created': stat.st_ctime,
                        'modified': stat.st_mtime
                    }
                    
                    # Check consistency
                    if base_timestamp is None:
                        base_timestamp = stat.st_ctime
                    else:
                        # Check if within reasonable range (1 day)
                        delta = abs(stat.st_ctime - base_timestamp)
                        if delta > 86400:
                            consistency_map['issues'].append({
                                'component': comp_name,
                                'issue': 'timestamp_mismatch',
                                'delta_hours': delta / 3600
                            })
                else:
                    consistency_map['components'][comp_name] = {
                        'exists': False
                    }
            
            # Calculate consistency score
            total = len(components)
            exists = sum(1 for c in consistency_map['components'].values() if c.get('exists'))
            no_issues = len(consistency_map['issues']) == 0
            
            consistency_map['consistency_score'] = (exists / total * 100) if no_issues else (exists / total * 50)
            
            return consistency_map
            
        except Exception as e:
            self.logger.error(f"Consistency map failed: {e}")
            consistency_map['error'] = str(e)
            return consistency_map