import pytest
from typer.testing import CliRunner
from ct_toolkit.cli import app
from ct_toolkit import __version__

runner = CliRunner()

def test_cli_help():
    """Test standard help output."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Computational Theseus Toolkit" in result.stdout
    assert "audit" in result.stdout

def test_cli_version():
    """Test --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"CT Toolkit v{__version__}" in result.stdout

def test_cli_list_kernels():
    """Test list-kernels command."""
    result = runner.invoke(app, ["list-kernels"])
    assert result.exit_code == 0
    assert "Available Kernels" in result.stdout
    # Check for a character that is definitely in the banner
    assert "____" in result.stdout

def test_cli_list_templates():
    """Test list-templates command."""
    result = runner.invoke(app, ["list-templates"])
    assert result.exit_code == 0
    assert "Available Templates" in result.stdout
    assert "general" in result.stdout

def test_cli_audit_invalid_url():
    """Test audit command with an unreachable URL (should fail gracefully)."""
    result = runner.invoke(app, ["audit", "--url", "http://invalid-url-that-does-not-exist:1234", "--kernel", "default"])
    
    # Check that it either failed with error or finished with 0%
    output = result.stdout.lower()
    assert (result.exit_code == 1) or (result.exit_code == 0 and "0.0%" in output)
    # At least some indicator of failure or starting should be there
    assert "starting audit" in output
