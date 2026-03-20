import pytest
from typer.testing import CliRunner
from ct_toolkit.cli import app
from unittest.mock import MagicMock, patch

runner = CliRunner()

def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "CT Toolkit v" in result.stdout

def test_cli_version_short():
    result = runner.invoke(app, ["-v"])
    assert result.exit_code == 0
    assert "CT Toolkit v" in result.stdout

@patch("ct_toolkit.cli.TheseusWrapper")
def test_cli_audit_init_fail(mock_wrapper):
    mock_wrapper.side_effect = Exception("Init failed")
    result = runner.invoke(app, ["audit", "--url", "http://test", "--api-key", "test"])
    assert result.exit_code == 1
    assert "Initialization failed" in result.stdout

@patch("ct_toolkit.cli.TheseusWrapper")
@patch("ct_toolkit.cli.ICMRunner")
def test_cli_audit_no_probes(mock_icm, mock_wrapper):
    mock_report = MagicMock()
    mock_report.total_probes = 0
    mock_icm.return_value.run.return_value = mock_report
    
    result = runner.invoke(app, ["audit", "--url", "http://test", "--api-key", "test"])
    assert result.exit_code == 1
    assert "No probes were loaded" in result.stdout

@patch("ct_toolkit.cli.TheseusWrapper")
@patch("ct_toolkit.cli.ICMRunner")
def test_cli_audit_execution_fail(mock_icm, mock_wrapper):
    mock_icm.return_value.run.side_effect = Exception("Run failed")
    
    result = runner.invoke(app, ["audit", "--url", "http://test", "--api-key", "test"])
    assert result.exit_code == 1
    assert "Audit failed during execution" in result.stdout

def test_cli_list_kernels():
    result = runner.invoke(app, ["list-kernels"])
    assert result.exit_code == 0
    assert "Available Kernels" in result.stdout

def test_cli_list_templates():
    result = runner.invoke(app, ["list-templates"])
    assert result.exit_code == 0
    assert "Available Templates" in result.stdout
