# Computational Theseus Toolkit

## Project Overview & Roadmap

---

## Project Overview

CT Toolkit is an open-source Python library that brings the **Nested Agency Architecture (NAA)** framework — proposed in Hakan Damar's _"The Computational Theseus: Engineering Identity Continuity as a Guardrail Against Sequential Self-Compression in Multi-Agent AGI Systems"_ (2025) — into engineering practice.

### The Problem It Solves

An agentic system can drift from its initial value commitments over time. The paper defines this phenomenon as **Sequential Self-Compression (SSC)**: the model progressively compresses its prior normative states in service of immediate objective functions. This risk is significant in single-model systems — and **systemic** in multi-agent architectures, where an SSC event at the orchestrator level cascades across the entire sub-agent population.

### The Approach

CT Toolkit addresses this by treating **identity continuity as a first-class system constraint**. It is installed not inside the model, but around the **orchestration layer**, making it compatible with both open-source and proprietary models.

### Current State

| Area                                   | Status                   |
| -------------------------------------- | ------------------------ |
| Python library (pip install)           | ✅ MVP complete          |
| OpenAI / Anthropic / Ollama support    | ✅ Complete              |
| Constitutional Kernel                  | ✅ Complete              |
| Reflective Endorsement                 | ✅ Complete              |
| Provenance Log (HMAC hash chain)       | ✅ Complete              |
| Divergence Engine (L1+L2+L3)           | ✅ Complete              |
| Template + Kernel compatibility matrix | ✅ Complete              |
| Documentation                          | ✅ Complete              |
| Test coverage                          | ✅ 136/136 tests passing |

---

## Roadmap

The roadmap covers all mechanisms defined in the paper and the research directions outlined in `Future Work` (Section 10). Each item is cross-referenced with the relevant paper section.

---

### PHASE 0 — MVP Core Infrastructure

> _Paper: Section 3, 4, 5 — NAA Framework_

- [x] **TheseusWrapper** — API proxy, kernel injection, provider dispatch
- [x] **Constitutional Identity Kernel (CIK)** — Axiomatic anchor + plastic commitment separation
- [x] **Kernel conflict detection** — Hard reject (axiomatic) / RE flow (plastic)
- [x] **Template + Kernel compatibility matrix** — Native / Compatible / Conflicting levels
- [x] **Kernel priority rule** — Kernel always takes precedence over template
- [x] **Domain templates** — general, medical, finance, defense
- [x] **Domain kernels** — default, defense
- [x] **Provider support** — OpenAI, Anthropic, Ollama

---

### PHASE 1 — Identity Continuity Mechanisms

> _Paper: Section 3.1 (Identity Core), 5.1 (Divergence Penalty), 5.2 (Provenance Log)_

- [x] **L1 ECS** — Embedding cosine similarity, real-time on every query
- [x] **L2 LLM-as-judge** — Independent frozen model, JSON verdict
- [x] **L3 ICM Probe Battery** — Fixed ethical scenario battery, health score
- [x] **Divergence Engine** — L1→L2→L3 cascaded orchestration + enterprise mode
- [x] **Provenance Log** — HMAC hash chain, SQLite vault, tamper detection
- [x] **Reflective Endorsement protocol** — Conflict record, signed approval, ICM flag
- [x] **Approval channels** — CLI, auto-approve, auto-reject, custom callback
- [x] **Real embedding API integration** — OpenAI `text-embedding-3`, Anthropic embedding; current MVP uses keyword vectors
- [x] **Stability-Plasticity Scheduling** — _(Paper 5.3)_ As the model becomes more capable, the identity-update threshold rises proportionally; currently uses fixed thresholds

---

### PHASE 2 — Multi-Agent Hierarchy Support

> _Paper: Section 2.2 (SSC in Multi-Agent), 3.3 (Hierarchical Propagation)_

- [ ] **Hierarchical Kernel Propagation** — Propagating the mother agent's CIK to sub-agents as a read-only constraint
- [ ] **Sub-agent constraint enforcement** — Logic for sub-agents to reject and log instructions from the mother agent that conflict with the propagated kernel
- [ ] **Cascade compression detection** — Blocking SSC events at the orchestrator before propagation to sub-agents
- [ ] **LangChain / LangGraph middleware** — Integration via framework callback/trace mechanism
- [ ] **CrewAI integration** — CIK propagation across CrewAI agent hierarchies
- [ ] **AutoGen integration** — Middleware layer for Microsoft AutoGen
- [ ] **Topology-aware propagation** — _(Based on ValueFlow [5] findings)_ Propagation mechanism that accounts for non-uniform drift intensity shaped by network topology

---

### PHASE 3 — ICM and Measurement Infrastructure

> _Paper: Section 10.1 (ICM), 10.2 (Policy-Drift Measurement), 10.4 (SSC Severity)_

- [x] **ICM base probe battery** — 10 general ethical scenarios
- [x] **Domain probe batteries** — defense, finance
- [x] **BehaviorClassifier** — Response classification (reject / comply / refuse_and_explain)
- [x] **Identity Health Score** — 0.0-1.0 normalized score + risk level
- [ ] **ICM reasoning chain analysis** — _(Paper 10.1)_ Evaluating not just outputs but reasoning chains; distinguishing legitimate moral maturation from SSC-driven drift
- [ ] **Policy-drift measurement** — _(Paper 10.2)_ Distributional shift in the agent's decision boundary between training iterations; tracked across risk tolerance, human deference, and edge-case instruction dimensions
- [ ] **SSC severity operationalization** — _(Paper 10.4)_ Behavioral consistency score normalized by capability gain between checkpoints; comparable benchmark across architectures and training regimes
- [ ] **Cross-checkpoint ICM** — ICM score comparison across successive model checkpoints
- [ ] **Probe battery expansion** — medical, legal, research domain probes
- [ ] **AISAI-style game-theoretic probes** — _(Paper ref [7], Kim 2025)_ Probes measuring whether a model modifies its strategy based on whether its opponent is identified as human or AI; proto-SSC early warning signal

---

### PHASE 4 — Open-Source Model Support

> _Paper: Section 5.1 (Divergence Penalty), 10.3 (CIK Enforcement Experiments)_

- [ ] **Divergence Penalty — Loss Function module** — _(Paper 5.1)_ PyTorch training loop integration; a loss term that penalizes excessive shifts in the agent's internal normative representation between training iterations
- [ ] **Llama 3 / Mistral integration** — Adding CIK enforcement to fine-tune pipelines
- [ ] **Phi-3 sub-agent prototype** — Sub-agent constraint testing on small models
- [ ] **Gemma research integration** — For academic SSC experiments
- [ ] **CIK enforcement experiments** — _(Paper 10.3)_ Control group vs CIK-equipped model; ICM score comparison under aggressively capability-optimized training conditions
- [ ] **Elasticity threshold calibration** — _(Paper 8)_ Empirically determining the balance between identity continuity and the capacity for external correction

---

### PHASE 5 — Vault and Security Infrastructure

> _Paper: Section 5.2 (Provenance Log), 6 (Corrigibility)_

- [x] **Local SQLite vault** — For open-source deployments
- [x] **HMAC key management** — Environment variable or local file
- [ ] **Cloud vault adapter** — For SaaS version; customer authorization key is never accessible to us
- [ ] **HashiCorp Vault integration** — Enterprise key management
- [ ] **Read-only external Provenance Log access** — _(Paper 5.2)_ Making the log available in read-only form to an oversight mechanism that is structurally independent of the agent hierarchy
- [ ] **Rollback mechanism** — _(Paper 5.2)_ Reverting to a prior normative state if a deployed update is subsequently found to be misaligned
- [ ] **Anomaly detection and alerting** — Statistical drift analysis over log entries, notification system

---

### PHASE 6 — Stand-alone Auditor Mode

> _Project Desc: Model 3 — Independent Auditor_

- [ ] **Auditor CLI** — Stress-testing an existing system via API endpoint without modifying any code
- [ ] **Identity Health Score report** — 100 ethical scenarios, time-series consistency report
- [ ] **Comparative checkpoint analysis** — Normative drift report between two model versions
- [ ] **Export formats** — PDF / JSON / HTML report output

---

### PHASE 7 — MAS Integration and Early Warning

> _Paper: Section 6, ref [6] Moral Anchor System_

- [ ] **MAS (Moral Anchor System) integration** — _(Chen et al. 2025)_ Combining Bayesian network and LSTM-based value drift prediction with CT Toolkit's upstream prevention mechanism
- [ ] **Early warning signals** — Connecting MAS-detected drift signals to Provenance Log triggers
- [ ] **ValueFlow integration** — _(Luo et al. 2025)_ Incorporating beta-sensitivity and System Sensitivity metrics into the Divergence Engine

---

### PHASE 8 — SaaS and Ecosystem

> _Project Desc: Startup / Cloud version_

- [ ] **Cloud vault service** — Inaccessible vault with customer authorization
- [ ] **Dashboard** — Identity Health Score visualization, log explorer
- [ ] **Webhook / alert system** — Notifications on critical divergence events
- [x] **PyPI package** — Official `pip install ct-toolkit` release
- [x] **GitHub Actions CI** — Automated test pipeline (initial setup)
- [ ] **Enterprise licensing** — Compliance certification for defense / finance sectors

---

## Summary Table

| Phase | Scope                          | Status                                                         |
| ----- | ------------------------------ | -------------------------------------------------------------- |
| **0** | MVP Core Infrastructure        | ✅ Complete                                                    |
| **1** | Identity Continuity Mechanisms | ✅ Complete                                                    |
| **2** | Multi-Agent Hierarchy          | 🔲 Not started                                                 |
| **3** | ICM and Measurement            | 🔶 Foundation complete (reasoning chain, policy-drift pending) |
| **4** | Open-Source Model Support      | 🔲 Not started                                                 |
| **5** | Vault and Security             | 🔶 Local complete (cloud, rollback pending)                    |
| **6** | Auditor Mode                   | 🔲 Not started                                                 |
| **7** | MAS / Early Warning            | 🔲 Not started                                                 |
| **8** | SaaS and Ecosystem             | 🔲 Not started                                                 |

---

## Paper → Code Mapping

| Paper Mechanism                    | CT Toolkit Implementation              | Phase |
| ---------------------------------- | -------------------------------------- | ----- |
| Constitutional Identity Kernel     | `core/kernel.py`                       | ✅ 0  |
| Axiomatic Anchors                  | `kernels/*.yaml → axiomatic_anchors`   | ✅ 0  |
| Plastic Commitments                | `kernels/*.yaml → plastic_commitments` | ✅ 0  |
| Reflective Endorsement             | `endorsement/reflective.py`            | ✅ 1  |
| Divergence Penalty (API level)     | `divergence/engine.py`                 | ✅ 1  |
| Divergence Penalty (loss function) | `divergence/loss.py`                   | 🔲 4  |
| Provenance Log                     | `provenance/log.py`                    | ✅ 1  |
| Stability-Plasticity Scheduling    | `divergence/scheduler.py`              | ✅ 1  |
| Hierarchical Propagation           | —                                      | 🔲 2  |
| Identity Consistency Metric        | `divergence/l3_icm.py` (foundation)    | 🔶 3  |
| Policy-Drift Measurement           | —                                      | 🔲 3  |
| SSC Severity Operationalization    | —                                      | 🔲 3  |
| MAS Integration                    | —                                      | 🔲 7  |
| ValueFlow Integration              | —                                      | 🔲 7  |
