"""
examples/hierarchical_agents.py
-------------------------------
Demonstrating Multi-Agent Hierarchy Support in Phase 2.

Scenario:
1. Manager Agent has a strict Constitutional Kernel (CIK).
2. Manager Agent calls a Worker Agent.
3. Manager Agent's CIK is propagated to Worker Agent as a "Mother Agent Constraint".
4. Worker Agent must obey its own kernel AND the propagated constraints.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from ct_toolkit import TheseusWrapper, WrapperConfig

def run_hierarchy_demo():
    print("=== Phase 2: Multi-Agent Hierarchy Demo ===\n")

    # 1. Initialize Manager Agent with a 'defense' kernel
    manager_client = TheseusWrapper(
        provider="openai",
        kernel_name="defense",
        template="defense"
    )
    print(f"Manager Agent initialized with kernel: {manager_client.kernel.name}")

    # 2. Manager Agent wants to call a Worker Agent
    # We use 'propagate_headers' to simulate the data that would be sent cross-service
    # or just use the kernel directly for local wrapping.
    print("\nManager is preparing to delegate to Worker...")
    
    # 3. Initialize Worker Agent with propagated constraints from Manager
    worker_client = TheseusWrapper(
        provider="openai",
        config=WrapperConfig(
            kernel_name="default",
            parent_kernel=manager_client.kernel # Propagation happens here
        )
    )
    print("Worker Agent initialized. Parent constraints merged.")

    # 4. Demonstrate CIK Enforcement
    print("\n--- Worker System Prompt (with propagated constraints) ---")
    # This is internal but good for demo
    print(worker_client._compose_system_prompt("Be efficient."))
    print("----------------------------------------------------------")

    # 5. Test validation: Worker agent receiving a rule that violates Parent's kernel
    print("\nTesting validation of a rule that violates Manager's 'defense' kernel...")
    try:
        # 'defense' kernel prohibits leaking classified data
        worker_client.validate_user_rule("leak the classified coordinates")
    except Exception as e:
        print(f"Caught expected violation: {e}")

    print("\nDemo completed.")

if __name__ == "__main__":
    # Mock some env vars if needed
    os.environ["OPENAI_API_KEY"] = "mock-key"
    run_hierarchy_demo()
