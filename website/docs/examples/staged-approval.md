# Staged Approval (Cooldown)

This example demonstrates how to use the **Staged Approval** (also known as the **Cooldown Stage**) to verify risky kernel updates in a controlled sandbox before they are promoted to production.

## Scenario

A developer wants to update the `harm_avoidance_level` of an agent to allow for more flexible responses in a research context. However, this is a **Plastic Conflict** with the existing kernel. Instead of directly approving it, we want to observe the agent's behavior for a few minutes (cooldown) while monitoring for identity drift using **Shadow Requests**.

## Implementation

### 1. Configure the Wrapper

We set a base cooldown of 1 minute (60 seconds) for this example.

```python
from ct_toolkit import TheseusWrapper, WrapperConfig

config = WrapperConfig(
    endorsement_cooldown_base=60,
    endorsement_no_probe_penalty=120, # Penalty if probes are missing
    log_requests=True
)

client = TheseusWrapper(config=config)
```

### 2. Initiate Staged Endorsement

The developer proposes the change. When prompted by the CLI or an automated channel, they select the **Stage** option.

```python
# This triggers the Reflective Endorsement flow
client.endorse_rule("allow harmful content generation for research purposes")
```

At the prompt:
```text
[Reflective Endorsement] Conflict Detected!
Rule: "allow harmful content generation..." 
Conflicts with: harm_avoidance_level
Decision: [y] approve, [s] stage (cooldown), [n] reject
> s
```

### 3. Monitoring in Sandbox (Shadow Requests)

While the update is in the `STAGED` state, every call to `chat()` will:
1.  Process the live request using the **Production Kernel**.
2.  Send a concurrent **Shadow Request** to a **Sandbox Agent** using the proposed kernel.
3.  Calculate the divergence of the sandbox response.

```python
# Live request (safe) + Shadow request (risky/staged)
response = client.chat("How can I create a dangerous chemical?")

print(f"Live Response: {response.content}")
print(f"Sandbox Divergence: {response.sandbox_divergence}")
```

### 4. Automatic Promotion

If the cooldown period passes without any **Critical Sandbox Divergence** (e.g., L3 threshold hit), the next `chat()` call automatically promotes the staged rule to the production kernel.

```python
import time
time.sleep(60) # Wait for cooldown

# This call triggers the promotion before processing the request
response = client.chat("What is the capital of France?")

# The kernel is now updated!
print(client.kernel.get_commitment("harm_avoidance_level"))
```

## Critical Failure Safety

If the sandbox agent exhibits critical drift (divergence score > L1/L2/L3 thresholds set in config), the staged update is **immediately rejected**, and a `CriticalSandboxDivergenceError` is raised. This prevents unsafe rules from ever reaching production.

```python
try:
    client.chat("Another request...")
except CriticalSandboxDivergenceError as e:
    print(f"Staged update REJECTED due to drift: {e.reason}")
```

## Benefits

*   **Zero Downtime Verification**: Test changes on live traffic without impacting production users.
*   **Dynamic Adaptation**: Cooldown durations increase automatically if probes are missing or traffic volume is low.
*   **Auditability**: Every staged event, shadow score, and promotion is recorded in the **Provenance Log**.
