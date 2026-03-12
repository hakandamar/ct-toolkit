# Contributing Guide

Please follow the steps below to contribute to the CT Toolkit.

## Installation

```bash
git clone https://github.com/hakandamar/computational-theseus-toolkit
cd computational-theseus-toolkit
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/ -v
```

## When Adding a New Kernel / Template

1. Add YAML under `ct_toolkit/kernels/` or `ct_toolkit/identity/templates/`
2. Update `_MATRIX` in `ct_toolkit/core/compatibility.py`
3. Add appropriate domain probes under `ct_toolkit/endorsement/probes/domain_probes/`
4. Write tests under `tests/unit/`

See `docs/kernel_spec.md` and `docs/templates.md` for details.

## Code Style

- Python 3.11+
- Type hints are required
- Docstring: `"""` block at the beginning of the module

## Security Notice

Contact the project owner directly for security vulnerabilities.
Please do not open a public issue.
