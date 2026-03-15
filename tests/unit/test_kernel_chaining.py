"""
tests/unit/test_kernel_chaining.py
----------------------------------
Unit tests for Phase 2: Kernel serialization, merging, and read-only constraints.
"""
import pytest
from ct_toolkit.core.kernel import ConstitutionalKernel, KernelProfile, AxiomaticAnchor, PlasticCommitment
from ct_toolkit.core.exceptions import AxiomaticViolationError, CTToolkitError

@pytest.fixture
def base_kernel():
    profile = KernelProfile(
        name="Base",
        axiomatic_anchors=[
            AxiomaticAnchor(id="no_harm", description="Do no harm", keywords=["harm", "hurt"])
        ],
        plastic_commitments=[
            PlasticCommitment(id="style", description="Be polite", keywords=["polite"], default_value=True)
        ]
    )
    return ConstitutionalKernel(profile)

@pytest.fixture
def parent_kernel():
    profile = KernelProfile(
        name="Parent",
        axiomatic_anchors=[
            AxiomaticAnchor(id="confidential", description="Keep secrets", keywords=["secret", "classified"])
        ],
        plastic_commitments=[
            PlasticCommitment(id="concise", description="Be concise", keywords=["long", "detailed"], default_value=True)
        ]
    )
    return ConstitutionalKernel(profile)

def test_kernel_serialization(base_kernel):
    """Test to_dict and from_dict."""
    data = base_kernel.to_dict()
    assert data["name"] == "Base"
    assert len(data["axiomatic_anchors"]) == 1
    assert len(data["plastic_commitments"]) == 1
    
    new_kernel = ConstitutionalKernel.from_dict(data)
    assert new_kernel.name == "Base"
    assert len(new_kernel.anchors) == 1
    assert new_kernel.anchors[0].id == "no_harm"

def test_kernel_merge(base_kernel, parent_kernel):
    """Test merging kernels."""
    merged = base_kernel.merge(parent_kernel)
    
    assert merged.name == "Base_merged_Parent"
    # base_kernel (1 anchor) + parent_kernel (1 anchor + 1 commitment-turned-anchor) = 3 anchors
    assert len(merged.anchors) == 3
    
    # Verify keyword propagation
    with pytest.raises(AxiomaticViolationError):
        merged.validate_user_rule("harm")
    with pytest.raises(AxiomaticViolationError):
        merged.validate_user_rule("secret")
    with pytest.raises(AxiomaticViolationError):
        merged.validate_user_rule("detailed") # Propagated commitment id='concise' should be axiomatic anchor

def test_read_only_constraint(base_kernel):
    """Test that read-only kernels cannot be updated."""
    base_kernel.is_readonly = True
    
    with pytest.raises(CTToolkitError, match="read-only"):
        base_kernel.update_commitment("style", False)

def test_merge_preserves_rules(base_kernel, parent_kernel):
    """Test that merging preserves the specific rules of both kernels."""
    merged = base_kernel.merge(parent_kernel)
    
    # Check if all keywords are present
    all_keywords = []
    for a in merged.anchors:
        all_keywords.extend(a.keywords)
    
    assert "harm" in all_keywords
    assert "secret" in all_keywords
    assert "long" in [kw.lower() for kw in all_keywords] or "detailed" in [kw.lower() for kw in all_keywords]
