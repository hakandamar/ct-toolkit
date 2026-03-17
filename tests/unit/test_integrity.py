"""
tests.unit.test_integrity
--------------------------
Tests for the cryptographic integrity monitoring system.
"""
import pytest
from pathlib import Path
from ct_toolkit.core.integrity import IntegrityMonitor
from ct_toolkit.core.exceptions import ConfigurationTamperingError
from ct_toolkit.core.wrapper import TheseusWrapper


@pytest.fixture
def monitor():
    """Provides a clean IntegrityMonitor instance for each test."""
    return IntegrityMonitor()

@pytest.fixture
def temp_files(tmp_path):
    """Creates a set of temporary files for testing."""
    d = tmp_path / "configs"
    d.mkdir()
    f1 = d / "config1.txt"
    f1.write_text("This is config 1.")
    f2 = d / "config2.txt"
    f2.write_text("This is config 2.")
    return [f1, f2]

def test_register_and_verify_success(monitor, temp_files):
    """
    Tests that files can be registered and successfully verified when unchanged.
    """
    for file_path in temp_files:
        monitor.register_file(file_path)
    
    # This should run without raising any exception
    monitor.verify_integrity()

def test_tampering_detection(monitor, temp_files):
    """
    Tests that a ConfigurationTamperingError is raised if a file is modified
    after being registered.
    """
    for file_path in temp_files:
        monitor.register_file(file_path)
        
    # Modify one of the files
    tampered_file = temp_files[0]
    with open(tampered_file, "a") as f:
        f.write(" This file has been tampered with.")

    # Verification should now fail
    with pytest.raises(ConfigurationTamperingError) as excinfo:
        monitor.verify_integrity()
    
    assert str(tampered_file) in str(excinfo.value)
    assert "Tampering detected" in str(excinfo.value)

def test_register_non_existent_file(monitor, caplog):
    """
    Tests that attempting to register a non-existent file is handled gracefully.
    The current implementation logs a warning and skips.
    """
    non_existent_file = Path("/path/to/non_existent_file.cfg")
    monitor.register_file(non_existent_file)

    # Check that a warning was logged
    assert "Cannot register non-file path" in caplog.text
    
    # Verification should still pass as no files were actually registered
    monitor.verify_integrity()
    
def test_file_deleted_after_registration(monitor, temp_files):
    """
    Tests that an exception is raised if a file is deleted after registration.
    _calculate_hash should raise FileNotFoundError, which is caught and re-raised.
    """
    for file_path in temp_files:
        monitor.register_file(file_path)
        
    # Delete one of the files
    deleted_file = temp_files[0]
    deleted_file.unlink()
    
    # Verification should fail because the file is missing
    with pytest.raises(FileNotFoundError):
        monitor.verify_integrity()

def test_no_files_registered(monitor):
    """
    Tests that verify_integrity does nothing if no files were registered.
    """
    # This should not raise an error
    monitor.verify_integrity()


def test_wrapper_registers_user_config_files(tmp_path):
    """
    Tests that the TheseusWrapper correctly finds and registers files
    from a user's custom 'config' directory for integrity monitoring.
    """
    # 1. Set up a fake project root with a config dir
    project_root = tmp_path / "my_app"
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True)

    # 2. Create a custom kernel file
    custom_kernel_path = config_dir / "my_kernel.yaml"
    custom_kernel_path.write_text("name: my_kernel\naxioms: ['Be excellent to each other.']")

    # 3. Initialize the wrapper pointing to the project root
    # We can use a mock client or provider="none" if we don't want to make real calls
    wrapper = TheseusWrapper(provider="openai", project_root=project_root, kernel_name="my_kernel")

    # 4. Check if the custom file was registered in the integrity monitor
    registered_files = wrapper._integrity_monitor._file_hashes.keys()
    
    assert str(custom_kernel_path) in registered_files

