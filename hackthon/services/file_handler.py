# File Handler Service - Secure file upload and processing for ACTMS

import os
import hashlib
import logging
from typing import Dict, Any, Optional, List
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import mimetypes
import pathlib

logger = logging.getLogger(__name__)

class FileHandler:
    def __init__(self, upload_folder: str = 'uploads'):
        self.upload_folder = upload_folder
        self.max_file_size = 15 * 1024 * 1024  # 15MB
        
        # Allowed file extensions and MIME types
        self.allowed_extensions = {
            '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt',
            '.xls', '.xlsx', '.csv', '.ods',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp',
            '.zip', '.rar', '.7z'
        }
        
        self.allowed_mime_types = {
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'text/rtf',
            'application/vnd.oasis.opendocument.text',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv',
            'application/vnd.oasis.opendocument.spreadsheet',
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/bmp',
            'application/zip',
            'application/x-rar-compressed',
            'application/x-7z-compressed'
        }
        
        # Dangerous file signatures to block
        self.dangerous_signatures = [
            b'\x4D\x5A',  # MZ (Windows executable)
            b'\x7F\x45\x4C\x46',  # ELF (Linux executable)
            b'\xCA\xFE\xBA\xBE',  # Java class file
            b'\x50\x4B\x03\x04',  # ZIP (check for executable content)
        ]
        
        # Ensure upload directory exists
        os.makedirs(upload_folder, exist_ok=True)
    
    def process_upload(self, file: FileStorage) -> Dict[str, Any]:
        """
        Process uploaded file with security validation
        
        Args:
            file: Werkzeug FileStorage object from Flask request
            
        Returns:
            Dictionary containing processing results
        """
        if not file:
            return {
                'success': False,
                'error': 'No file provided',
                'file_path': None,
                'file_hash': None,
                'file_info': {}
            }
        
        try:
            # Validate file
            validation_result = self._validate_file(file)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'file_path': None,
                    'file_hash': None,
                    'file_info': validation_result.get('file_info', {})
                }
            
            # Generate secure filename and path
            filename = file.filename if file.filename else 'upload'
            secure_name = self._generate_secure_filename(filename)
            file_path = os.path.join(self.upload_folder, secure_name)
            
            # Calculate file hash before saving
            file.seek(0)  # Reset file pointer
            file_content = file.read()
            file_hash = self._calculate_file_hash(file_content)
            
            # Check for duplicate files
            if self._file_exists_by_hash(file_hash):
                logger.info(f"Duplicate file detected with hash: {file_hash}")
                return {
                    'success': True,
                    'message': 'File already exists (duplicate detected)',
                    'file_path': file_path,
                    'file_hash': file_hash,
                    'file_info': validation_result['file_info'],
                    'duplicate': True
                }
            
            # Save file securely
            file.seek(0)  # Reset file pointer for saving
            file.save(file_path)
            
            # Set secure file permissions (read-only for others)
            os.chmod(file_path, 0o644)
            
            # Final security scan of saved file
            final_scan = self._scan_saved_file(file_path)
            if not final_scan['safe']:
                # Remove unsafe file
                try:
                    os.remove(file_path)
                except OSError:
                    pass
                
                return {
                    'success': False,
                    'error': f'File failed security scan: {final_scan["reason"]}',
                    'file_path': None,
                    'file_hash': None,
                    'file_info': validation_result['file_info']
                }
            
            logger.info(f"File uploaded successfully: {secure_name} (hash: {file_hash})")
            
            return {
                'success': True,
                'message': 'File uploaded successfully',
                'file_path': file_path,
                'file_hash': file_hash,
                'file_info': {
                    **validation_result['file_info'],
                    'saved_filename': secure_name,
                    'upload_timestamp': self._get_current_timestamp()
                },
                'duplicate': False
            }
            
        except Exception as e:
            logger.error(f"File upload processing error: {str(e)}")
            return {
                'success': False,
                'error': f'Upload processing failed: {str(e)}',
                'file_path': None,
                'file_hash': None,
                'file_info': {}
            }
    
    def _validate_file(self, file: FileStorage) -> Dict[str, Any]:
        """Validate uploaded file against security criteria"""
        try:
            # Check if filename exists
            if not file.filename:
                return {
                    'valid': False,
                    'error': 'No filename provided',
                    'file_info': {}
                }
            
            # Get file extension
            file_ext = pathlib.Path(file.filename).suffix.lower()
            
            # Check file extension
            if file_ext not in self.allowed_extensions:
                return {
                    'valid': False,
                    'error': f'File type not allowed: {file_ext}',
                    'file_info': {'extension': file_ext}
                }
            
            # Check MIME type
            mime_type, _ = mimetypes.guess_type(file.filename)
            if mime_type and mime_type not in self.allowed_mime_types:
                return {
                    'valid': False,
                    'error': f'MIME type not allowed: {mime_type}',
                    'file_info': {'extension': file_ext, 'mime_type': mime_type}
                }
            
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  # Reset position
            
            if file_size > self.max_file_size:
                return {
                    'valid': False,
                    'error': f'File too large: {file_size} bytes (max: {self.max_file_size})',
                    'file_info': {'extension': file_ext, 'mime_type': mime_type, 'size': file_size}
                }
            
            if file_size == 0:
                return {
                    'valid': False,
                    'error': 'Empty file not allowed',
                    'file_info': {'extension': file_ext, 'mime_type': mime_type, 'size': file_size}
                }
            
            # Check file signature for dangerous content
            file_content = file.read(1024)  # Read first 1KB for signature check
            file.seek(0)  # Reset position
            
            signature_check = self._check_file_signature(file_content)
            if not signature_check['safe']:
                return {
                    'valid': False,
                    'error': signature_check['reason'],
                    'file_info': {'extension': file_ext, 'mime_type': mime_type, 'size': file_size}
                }
            
            # Filename security check
            filename_check = self._validate_filename(file.filename)
            if not filename_check['safe']:
                return {
                    'valid': False,
                    'error': filename_check['reason'],
                    'file_info': {'extension': file_ext, 'mime_type': mime_type, 'size': file_size}
                }
            
            return {
                'valid': True,
                'error': None,
                'file_info': {
                    'original_filename': file.filename,
                    'extension': file_ext,
                    'mime_type': mime_type,
                    'size': file_size
                }
            }
            
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return {
                'valid': False,
                'error': f'Validation failed: {str(e)}',
                'file_info': {}
            }
    
    def _check_file_signature(self, content: bytes) -> Dict[str, Any]:
        """Check file signature for dangerous content"""
        try:
            # Check for dangerous file signatures
            for signature in self.dangerous_signatures:
                if content.startswith(signature):
                    return {
                        'safe': False,
                        'reason': 'Dangerous file signature detected'
                    }
            
            # Additional checks for script content in text files
            if b'<script' in content.lower() or b'javascript:' in content.lower():
                return {
                    'safe': False,
                    'reason': 'Potential script content detected'
                }
            
            # Check for embedded executables in documents
            if b'This program cannot be run in DOS mode' in content:
                return {
                    'safe': False,
                    'reason': 'Embedded executable detected'
                }
            
            return {'safe': True, 'reason': None}
            
        except Exception as e:
            logger.warning(f"File signature check error: {str(e)}")
            return {'safe': True, 'reason': None}  # Fail open for signature check
    
    def _validate_filename(self, filename: str) -> Dict[str, Any]:
        """Validate filename for security issues"""
        try:
            # Check for path traversal attempts
            if '..' in filename or '/' in filename or '\\' in filename:
                return {
                    'safe': False,
                    'reason': 'Path traversal attempt in filename'
                }
            
            # Check for null bytes
            if '\x00' in filename:
                return {
                    'safe': False,
                    'reason': 'Null byte in filename'
                }
            
            # Check filename length
            if len(filename) > 255:
                return {
                    'safe': False,
                    'reason': 'Filename too long'
                }
            
            # Check for reserved names (Windows)
            reserved_names = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                             'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 
                             'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
            
            filename_base = pathlib.Path(filename).stem.upper()
            if filename_base in reserved_names:
                return {
                    'safe': False,
                    'reason': 'Reserved filename not allowed'
                }
            
            return {'safe': True, 'reason': None}
            
        except Exception as e:
            logger.warning(f"Filename validation error: {str(e)}")
            return {'safe': True, 'reason': None}  # Fail open for filename validation
    
    def _generate_secure_filename(self, original_filename: str) -> str:
        """Generate secure filename with timestamp"""
        try:
            # Use werkzeug's secure_filename
            base_name = secure_filename(original_filename)
            
            # If secure_filename returns empty string, use default
            if not base_name:
                base_name = 'upload'
            
            # Add timestamp to prevent conflicts
            import time
            timestamp = str(int(time.time()))
            
            # Split filename and extension
            name_parts = base_name.rsplit('.', 1)
            if len(name_parts) == 2:
                name, ext = name_parts
                secure_name = f"{name}_{timestamp}.{ext}"
            else:
                secure_name = f"{base_name}_{timestamp}"
            
            return secure_name
            
        except Exception as e:
            logger.error(f"Secure filename generation error: {str(e)}")
            import time
            return f"upload_{int(time.time())}"
    
    def _calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content"""
        try:
            return hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.error(f"File hash calculation error: {str(e)}")
            return ""
    
    def _file_exists_by_hash(self, file_hash: str) -> bool:
        """Check if file with same hash already exists"""
        try:
            # This could be expanded to check database records
            # For now, just return False to allow all uploads
            return False
        except Exception:
            return False
    
    def _scan_saved_file(self, file_path: str) -> Dict[str, Any]:
        """Final security scan of saved file"""
        try:
            # Check if file still exists and is readable
            if not os.path.exists(file_path):
                return {
                    'safe': False,
                    'reason': 'File disappeared after save'
                }
            
            # Check file size consistency
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return {
                    'safe': False,
                    'reason': 'File size exceeds limit after save'
                }
            
            # Re-read first part of file for signature check
            with open(file_path, 'rb') as f:
                content = f.read(1024)
                signature_check = self._check_file_signature(content)
                if not signature_check['safe']:
                    return signature_check
            
            return {'safe': True, 'reason': None}
            
        except Exception as e:
            logger.error(f"Final file scan error: {str(e)}")
            return {
                'safe': False,
                'reason': f'Scan failed: {str(e)}'
            }
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp string"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def delete_file(self, file_path: str) -> bool:
        """Safely delete uploaded file"""
        try:
            if os.path.exists(file_path) and file_path.startswith(self.upload_folder):
                os.remove(file_path)
                logger.info(f"File deleted: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"File deletion error: {str(e)}")
            return False
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get information about uploaded file"""
        try:
            if not os.path.exists(file_path):
                return None
            
            stat = os.stat(file_path)
            return {
                'path': file_path,
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'permissions': oct(stat.st_mode)[-3:]
            }
        except Exception as e:
            logger.error(f"File info error: {str(e)}")
            return None