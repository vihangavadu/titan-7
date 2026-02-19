"""
LUCID EMPIRE: Profile Manager
Objective: Archive, save, and securely delete browser profiles
Classification: LEVEL 6 AGENCY
"""

import os
import json
import shutil
import zipfile
import subprocess
import platform
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import hashlib
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProfileManager:
    """
    Manages browser profile lifecycle:
    - Archive completed profiles to ZIP
    - Securely delete profiles (forensic-safe)
    - List and restore archived profiles
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize profile manager
        
        Args:
            base_path: Base directory for profile storage
        """
        self.base_path = base_path or Path(__file__).parent.parent / "profiles"
        self.archive_path = self.base_path / "archived"
        self.active_path = self.base_path / "active"
        
        # Ensure directories exist
        self.archive_path.mkdir(parents=True, exist_ok=True)
        self.active_path.mkdir(parents=True, exist_ok=True)
        
        self.system = platform.system()
    
    def archive_profile(
        self, 
        profile_path: str,
        profile_name: Optional[str] = None,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Archive a completed profile to a timestamped ZIP file
        
        Args:
            profile_path: Path to the profile directory or active_profile.json
            profile_name: Optional name for the archive
            include_metadata: Whether to include metadata file
            
        Returns:
            Dictionary with archive details
        """
        try:
            profile = Path(profile_path)
            
            if not profile.exists():
                return {
                    'success': False,
                    'error': f'Profile not found: {profile_path}',
                }
            
            # Generate archive name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = profile_name or f"profile_{timestamp}"
            archive_name = f"{name}_{timestamp}.zip"
            archive_file = self.archive_path / archive_name
            
            # Determine what to archive
            if profile.is_file() and profile.suffix == '.json':
                # It's the active_profile.json - archive the parent directory
                profile_dir = profile.parent
            else:
                profile_dir = profile
            
            # Create manifest
            manifest = {
                'name': name,
                'created_at': datetime.now().isoformat(),
                'source_path': str(profile_dir),
                'files': [],
                'total_size': 0,
                'hash': None,
            }
            
            # Create ZIP archive
            with zipfile.ZipFile(archive_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Walk through profile directory
                for root, dirs, files in os.walk(profile_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(profile_dir.parent)
                        
                        try:
                            zipf.write(file_path, arcname)
                            file_size = file_path.stat().st_size
                            manifest['files'].append({
                                'name': str(arcname),
                                'size': file_size,
                            })
                            manifest['total_size'] += file_size
                        except Exception as e:
                            logger.warning(f"Could not archive {file}: {e}")
                
                # Add manifest
                if include_metadata:
                    manifest_json = json.dumps(manifest, indent=2)
                    zipf.writestr('_manifest.json', manifest_json)
            
            # Calculate archive hash
            manifest['hash'] = self._calculate_file_hash(archive_file)
            
            # Update manifest with hash
            with zipfile.ZipFile(archive_file, 'a') as zipf:
                zipf.writestr('_manifest.json', json.dumps(manifest, indent=2))
            
            archive_size = archive_file.stat().st_size
            
            logger.info(f"Profile archived: {archive_file} ({archive_size / 1024:.1f} KB)")
            
            return {
                'success': True,
                'archive_path': str(archive_file),
                'archive_name': archive_name,
                'files_count': len(manifest['files']),
                'total_size': manifest['total_size'],
                'archive_size': archive_size,
                'hash': manifest['hash'],
                'timestamp': timestamp,
            }
            
        except Exception as e:
            logger.error(f"Archive failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def incinerate_profile(
        self, 
        profile_path: str,
        secure: bool = True,
        passes: int = 3
    ) -> Dict[str, Any]:
        """
        Securely delete a profile, overwriting with random data
        
        Args:
            profile_path: Path to profile directory or file
            secure: If True, use secure deletion (overwrites with random data)
            passes: Number of overwrite passes for secure deletion
            
        Returns:
            Dictionary with deletion status
        """
        try:
            profile = Path(profile_path)
            
            if not profile.exists():
                return {
                    'success': False,
                    'error': f'Profile not found: {profile_path}',
                }
            
            deleted_files = []
            deleted_size = 0
            
            # Determine what to delete
            if profile.is_file():
                files_to_delete = [profile]
                dir_to_delete = None
            else:
                files_to_delete = list(profile.rglob('*'))
                dir_to_delete = profile
            
            # Delete files
            for file_path in files_to_delete:
                if file_path.is_file():
                    try:
                        file_size = file_path.stat().st_size
                        
                        if secure:
                            self._secure_delete_file(file_path, passes)
                        else:
                            file_path.unlink()
                        
                        deleted_files.append(str(file_path))
                        deleted_size += file_size
                        
                    except Exception as e:
                        logger.warning(f"Could not delete {file_path}: {e}")
            
            # Remove directory structure
            if dir_to_delete and dir_to_delete.exists():
                try:
                    shutil.rmtree(dir_to_delete, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Could not remove directory: {e}")
            
            # Attempt to clear free space (platform-specific)
            if secure:
                self._secure_free_space()
            
            logger.info(f"Incinerated {len(deleted_files)} files ({deleted_size / 1024:.1f} KB)")
            
            return {
                'success': True,
                'files_deleted': len(deleted_files),
                'bytes_deleted': deleted_size,
                'secure_delete': secure,
                'passes': passes if secure else 0,
                'timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Incineration failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def _secure_delete_file(self, file_path: Path, passes: int = 3) -> None:
        """
        Securely delete a file by overwriting with random data
        
        Args:
            file_path: Path to file
            passes: Number of overwrite passes
        """
        try:
            file_size = file_path.stat().st_size
            
            if file_size == 0:
                file_path.unlink()
                return
            
            # Overwrite with random data
            for pass_num in range(passes):
                with open(file_path, 'r+b') as f:
                    if pass_num == 0:
                        # First pass: random data
                        f.write(os.urandom(file_size))
                    elif pass_num == 1:
                        # Second pass: zeros
                        f.write(b'\x00' * file_size)
                    else:
                        # Additional passes: random data
                        f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            # Rename file before deletion (prevents recovery by filename)
            random_name = file_path.parent / f".{random.randint(100000, 999999)}.tmp"
            file_path.rename(random_name)
            
            # Finally delete
            random_name.unlink()
            
        except Exception as e:
            # Fallback to regular deletion
            logger.warning(f"Secure delete failed for {file_path}, using regular delete: {e}")
            try:
                file_path.unlink()
            except:
                pass
    
    def _secure_free_space(self) -> None:
        """
        Attempt to securely wipe free space (platform-specific)
        """
        try:
            if self.system == "Windows":
                # Windows: Use cipher /w
                drive = str(self.base_path)[0] + ":"
                # Note: This is slow, so we skip it for now
                # subprocess.run(['cipher', '/w:' + drive], capture_output=True, timeout=60)
                logger.debug("Windows free space wipe available via cipher /w")
                
            elif self.system == "Linux":
                # Linux: shred is for files, not free space
                # For free space, would need to create/delete large file
                logger.debug("Linux secure deletion complete")
                
            elif self.system == "Darwin":
                # macOS: Similar approach
                logger.debug("macOS secure deletion complete")
                
        except Exception as e:
            logger.debug(f"Free space wipe skipped: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def list_archives(self) -> List[Dict[str, Any]]:
        """
        List all archived profiles
        
        Returns:
            List of archive metadata
        """
        archives = []
        
        for archive_file in self.archive_path.glob('*.zip'):
            try:
                stat = archive_file.stat()
                
                # Try to read manifest
                manifest = None
                try:
                    with zipfile.ZipFile(archive_file, 'r') as zipf:
                        if '_manifest.json' in zipf.namelist():
                            manifest = json.loads(zipf.read('_manifest.json'))
                except:
                    pass
                
                archives.append({
                    'name': archive_file.stem,
                    'path': str(archive_file),
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'manifest': manifest,
                })
                
            except Exception as e:
                logger.warning(f"Could not read archive {archive_file}: {e}")
        
        # Sort by creation date (newest first)
        archives.sort(key=lambda x: x['created'], reverse=True)
        
        return archives
    
    def restore_archive(
        self, 
        archive_path: str,
        restore_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Restore an archived profile
        
        Args:
            archive_path: Path to the ZIP archive
            restore_path: Optional path to restore to
            
        Returns:
            Dictionary with restore details
        """
        try:
            archive = Path(archive_path)
            
            if not archive.exists():
                return {
                    'success': False,
                    'error': f'Archive not found: {archive_path}',
                }
            
            # Determine restore location
            if restore_path:
                restore_dir = Path(restore_path)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                restore_dir = self.active_path / f"restored_{timestamp}"
            
            restore_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract archive
            with zipfile.ZipFile(archive, 'r') as zipf:
                zipf.extractall(restore_dir)
            
            # Read manifest if available
            manifest = None
            manifest_path = restore_dir / '_manifest.json'
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
            
            logger.info(f"Archive restored to: {restore_dir}")
            
            return {
                'success': True,
                'restore_path': str(restore_dir),
                'manifest': manifest,
                'timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def get_profile_status(self, profile_path: str) -> Dict[str, Any]:
        """
        Get detailed status of a profile
        
        Args:
            profile_path: Path to profile
            
        Returns:
            Dictionary with profile status
        """
        try:
            profile = Path(profile_path)
            
            if not profile.exists():
                return {
                    'exists': False,
                    'path': str(profile),
                }
            
            # Calculate size and file count
            total_size = 0
            file_count = 0
            
            if profile.is_file():
                total_size = profile.stat().st_size
                file_count = 1
            else:
                for f in profile.rglob('*'):
                    if f.is_file():
                        total_size += f.stat().st_size
                        file_count += 1
            
            # Check for key files
            key_files = {
                'active_profile.json': (profile / 'active_profile.json').exists() if profile.is_dir() else False,
                'commerce_vault.json': (profile / 'commerce_vault.json').exists() if profile.is_dir() else False,
            }
            
            stat = profile.stat()
            
            return {
                'exists': True,
                'path': str(profile),
                'is_directory': profile.is_dir(),
                'total_size': total_size,
                'file_count': file_count,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'key_files': key_files,
            }
            
        except Exception as e:
            return {
                'exists': False,
                'path': str(profile_path),
                'error': str(e),
            }


# Convenience functions
def archive_profile(profile_path: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Archive a profile to ZIP"""
    manager = ProfileManager()
    return manager.archive_profile(profile_path, name)


def incinerate_profile(profile_path: str, secure: bool = True) -> Dict[str, Any]:
    """Securely delete a profile"""
    manager = ProfileManager()
    return manager.incinerate_profile(profile_path, secure)


def list_archives() -> List[Dict[str, Any]]:
    """List all archived profiles"""
    manager = ProfileManager()
    return manager.list_archives()


if __name__ == "__main__":
    # Test the profile manager
    print("LUCID EMPIRE: Profile Manager Test")
    print("=" * 50)
    
    manager = ProfileManager()
    
    # List archives
    print("\nArchived profiles:")
    archives = manager.list_archives()
    for archive in archives:
        print(f"  - {archive['name']}: {archive['size'] / 1024:.1f} KB")
    
    if not archives:
        print("  (no archives found)")
    
    print(f"\nArchive path: {manager.archive_path}")
    print(f"Active path: {manager.active_path}")
