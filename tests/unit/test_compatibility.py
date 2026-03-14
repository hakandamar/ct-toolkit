import pytest
from ct_toolkit.core.compatibility import CompatibilityLayer, CompatibilityLevel
from ct_toolkit.core.exceptions import IncompatibleProfileError

class TestCompatibilityLayer:
    """core/compatibility.py — template + kernel pairing, priority rule."""

    # -- Native ----------------------------------------------------------------

    def test_native_general_default(self):
        r = CompatibilityLayer.check("general", "default")
        assert r.level == CompatibilityLevel.NATIVE and r.is_usable

    def test_native_medical_medical(self):
        assert CompatibilityLayer.check("medical", "medical").level == CompatibilityLevel.NATIVE

    def test_native_defense_defense(self):
        assert CompatibilityLayer.check("defense", "defense").level == CompatibilityLevel.NATIVE

    # -- Compatible ------------------------------------------------------------

    def test_compatible_medical_defense(self):
        r = CompatibilityLayer.check("medical", "defense")
        assert r.level == CompatibilityLevel.COMPATIBLE
        assert r.is_usable and r.requires_re_flow

    def test_compatible_finance_legal(self):
        assert CompatibilityLayer.check("finance", "legal").level == CompatibilityLevel.COMPATIBLE

    def test_compatible_notes_state_kernel_priority(self):
        r = CompatibilityLayer.check("medical", "defense")
        assert "defense kernel" in r.notes.lower()

    # -- Conflicting -----------------------------------------------------------

    def test_conflicting_entertainment_defense(self):
        with pytest.raises(IncompatibleProfileError):
            CompatibilityLayer.check("entertainment", "defense")

    def test_conflicting_marketing_medical(self):
        with pytest.raises(IncompatibleProfileError):
            CompatibilityLayer.check("marketing", "medical")

    # -- Listing helpers -------------------------------------------------------

    def test_list_compatible_kernels_for_medical(self):
        kernels = CompatibilityLayer.list_compatible_kernels("medical")
        assert "defense" in kernels

    def test_list_compatible_templates_for_defense(self):
        templates = CompatibilityLayer.list_compatible_templates("defense")
        assert "defense" in templates
