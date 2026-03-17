"""
ct_toolkit.core.integrity
-------------------------
Cryptographic integrity monitoring for configuration files.
"""
import hashlib
from pathlib import Path
from ct_toolkit.utils.logger import get_logger
from ct_toolkit.core.exceptions import ConfigurationTamperingError

logger = get_logger(__name__)

class IntegrityMonitor:
    """
    Monitors the cryptographic integrity of CT configuration files.
    Prevents runtime tampering by agents or malicious actors.
    """
    def __init__(self):
        self._file_hashes: dict[str, str] = {}

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculates the SHA-256 hash of a given file."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                buf = f.read()
                hasher.update(buf)
            return hasher.hexdigest()
        except FileNotFoundError:
            logger.error(f"Integrity check failed: File not found at {file_path}")
            raise

    def register_file(self, file_path: Path) -> None:
        """Registers a file and stores its initial hash."""
        if not file_path.is_file():
            logger.warning(f"Integrity check: Cannot register non-file path: {file_path}")
            return
        
        file_hash = self._calculate_hash(file_path)
        self._file_hashes[str(file_path)] = file_hash
        logger.debug(f"Registered integrity hash for {file_path.name}")

    def verify_integrity(self) -> None:
        """
        Verifies that none of the registered files have been modified.
        Raises ConfigurationTamperingError if a mismatch is found.
        """
        if not self._file_hashes:
            return  # Nothing to verify

        for path_str, original_hash in self._file_hashes.items():
            current_hash = self._calculate_hash(Path(path_str))
            if current_hash != original_hash:
                raise ConfigurationTamperingError(path_str)
        logger.debug("Integrity verification passed for all registered files.")

