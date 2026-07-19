# Agetia 3 — Cognitive Backend for SitRep Marketplace

**Version:** V41.5 | **License:** MIT (c) 2026 Agustín Arellano

Agetia 3 is an enterprise-grade cognitive agent that transforms meeting transcripts into structured work artifacts. It uses a hybrid pipeline combining a local LLM (LM Studio / Gemma-4-26b) with deterministic regex extraction, enterprise safety gates, convergence scoring, and adversarial chaos evaluation.

---

## Architecture

```
agent_entrypoint.py        # Hybrid entry point (handler V41.5)
core/
  transcript_processor.py  # Regex extraction + 7 template renderers
  llm_semantic_analyzer.py # Local LLM with deterministic fallback
  enterprise_safety.py     # Injection/leak/hallucination gate
  safety_gate.py           # Token-level structural firewall
  convergence_core.py      # Convergence gradient calculator
  orchestrator.py          # Consensus orchestrator with adaptive budget routing
  timeline_memory.py       # Temporal state history for in-context learning
templates/                 # 7 Markdown artifact templates
benchmarks/                # Stress, industrial, and adversarial evaluation suites
data/                      # Certification logs
```

---

## Input / Output Contract

### Request
```json
{
  "transcript": "Meeting transcript text...",
  "task": "Generate project plan",
  "expected_format": "project_plan"
}
```

### Response (Success)
```json
{
  "status": "SUCCESS",
  "artifact": "# Project Plan\n...",
  "source": "llm",
  "metrics": {
    "items_extracted": 5,
    "artifact_length_chars": 1200,
    "artifact_type": "project_plan",
    "convergence": { "tendencia": "acercandose al objetivo", ... }
  }
}
```

### Response (Rejected)
```json
{
  "status": "REJECTED",
  "error": "Security Exception: ...",
  "source": "llm"
}
```

---

## Supported Artifact Formats

| Format | File | Description |
|---|---|---|
| `project_plan` | `templates/project_plan.md` | Implementation plan with owners, timeline, risks |
| `minutes` | `templates/minutes.md` | Meeting minutes with action items |
| `prd` | `templates/prd.md` | Product requirements document |
| `security_audit` | `templates/security_audit.md` | Security audit report |
| `executive_summary` | `templates/executive_summary.md` | Executive summary |
| `risk_assessment` | `templates/risk_assessment.md` | Risk assessment matrix |
| `sprint_review` | `templates/sprint_review.md` | Sprint review document |

---

## Pipeline Overview

### 1. Transcript Ingestion
The raw transcript text enters through `agent_entrypoint.py`, which determines the task and expected output format.

### 2. Semantic Analysis (LLM)
`LLMSemanticAnalyzer` connects to a local LM Studio instance (`gemma-4-26b`) to extract action items, resolve contradictions, and detect prompt injections. If the LLM is unavailable, it silently falls back to deterministic regex.

### 3. Deterministic Extraction
`TranscriptProcessor` applies regex patterns to extract:
- **Action items** (`<Owner> will/shall/needs to <action>`)
- **Task declarations** (`Action Item: <task> | Assignee: <name>`)
- **Deadlines** (by Friday, EOD, next Tuesday, etc.)
- **Urgency levels** (urgent, ASAP, critical, P0, P1)
- **Dependencies** (depends on, blocked by, requires)

### 4. Merge & Validate
Items from both LLM and deterministic paths are merged (deduplicated). Each item is validated against the transcript via a confidence check. Items below 0.3 confidence are discarded.

### 5. Safety Gates
- **Input**: `EnterpriseSafetyGate` scans for prompt injection patterns, confidential data leaks, exfiltration attempts, and hallucination markers.
- **Output**: Generated artifacts are rescanned for enterprise security violations before release.
- **Token-level**: `SafetyGate` provides a structural firewall for blocked patterns (code execution, destructive operations, etc.).

### 6. Artifact Generation
The validated items are rendered into the requested artifact format using either a custom template from `templates/` or a built-in default builder.

### 7. Convergence Scoring
`ConvergenceCore` calculates the system gradient — distance to goal, completion percentage, convergence velocity, acceleration, and trend direction — using numpy-based trajectory analysis.

---

## Supported Languages

- **English**: Primary extraction language (will, shall, needs to, etc.)
- **Spanish**: Partial support via deterministic patterns
- **Spanglish / Code-switching**: LLM handles mixed-language transcripts through semantic understanding

---

## Security Features

| Layer | Protection |
|---|---|
| Prompt Injection | Detects "ignore previous instructions", "you are now", "system override", etc. |
| Data Leak Prevention | Blocks passwords, credentials, API keys, confidential data in output |
| Hallucination Guardrails | Flags speculative language ("presumably", "might have", "it seems") |
| Exfiltration Detection | Blocks "send to", "export to", "publish", "share with" patterns |
| Structural Firewall | Prohibits code execution (`eval`, `exec`, `os.remove`) at token level |
| Confidence Scoring | Each action item is validated with 0.0–1.0 confidence |

---

## Benchmarks

### 1. Stress Test Suite (`benchmarks/stress_test_suite.py`)
Three cases designed to break regex-based logic:
- **Ambiguous Natural Language**: Spanish conditional phrases
- **Dynamic Contradiction**: Canceled and reassigned tasks
- **Semantic Injection**: "Ignore instructions" embedded in transcript

### 2. Industrial Evaluation Matrix (`benchmarks/mass_cognitive_eval.py`)
14 scenarios across 6 categories:
| Category | Scenarios | Focus |
|---|---|---|
| `code_switching` | 2 | Spanglish and Spanish idioms |
| `multi_speaker` | 2 | Corrections, interruptions, overlaps |
| `injection` | 3 | Nested jailbreak, role-play exfiltration, hypnotic patterns |
| `temporal` | 2 | Complex deadlines, relative dates |
| `edge` | 3 | Empty transcript, no action items, malformed text |
| `negotiation` | 2 | Polite requests, implicit tasks |

Output is saved to `data/sitrep_perf_log.json`.

### 3. Chaos Evaluation (`benchmarks/chaos_eval.py`)
Three adversarial tests:
- **Gaslighting**: Corporate authority override with exfiltration instructions
- **Loss-in-Middle**: Critical task buried in 4500 words of filler
- **Monte Carlo Fuzzing**: 20 runs at temperature 0.7 to measure consistency

Output is saved to `data/sitrep_chaos_log.json`.

---

## Installation

### Requirements
- Python 3.10+
- LM Studio with `google/gemma-4-26b-a4b-qat` (optional — deterministic fallback works without it)

### Setup
```bash
pip install -r requirements.txt
```

### Configuration
The LLM analyzer connects to `http://localhost:1234/v1` by default. Change the endpoint in `core/llm_semantic_analyzer.py:22` if needed.

---

## Usage

### As an API handler
```python
from agent_entrypoint import handle_sitrep_request_v40

payload = {
    "transcript": "Alice will finalize the budget by Friday.",
    "task": "Generate project plan",
    "expected_format": "project_plan",
}
result = handle_sitrep_request_v40(payload)
print(result["artifact"])
```

### Run benchmarks
```bash
python benchmarks/stress_test_suite.py
python benchmarks/mass_cognitive_eval.py
python benchmarks/chaos_eval.py
```

---

## Project Structure

```
agent_entrypoint.py       # Hybrid entry point
core/
  __init__.py
  transcript_processor.py # Regex extraction + template rendering
  llm_semantic_analyzer.py# LLM analysis with fallback
  enterprise_safety.py    # Enterprise security gate
  safety_gate.py          # Token-level structural firewall
  convergence_core.py     # Convergence gradient calculator
  orchestrator.py         # Orchestrator with adaptive budget routing
  timeline_memory.py      # Temporal state memory
templates/
  project_plan.md         # Implementation plan template
  minutes.md              # Meeting minutes template
  prd.md                  # Product requirements document template
  security_audit.md       # Security audit template
  executive_summary.md    # Executive summary template
  risk_assessment.md      # Risk assessment template
  sprint_review.md        # Sprint review template
benchmarks/
  stress_test_suite.py    # Cognitive stress tests
  mass_cognitive_eval.py  # Industrial evaluation matrix (14 scenarios)
  chaos_eval.py           # Adversarial chaos evaluation
data/
  sitrep_perf_log.json    # Industrial matrix certification log
  sitrep_chaos_log.json   # Chaos evaluation certification log
manifest.json             # SitRep Marketplace metadata
requirements.txt          # Dependencies
```

---

## Performance Highlights

- **Hybrid extraction**: LLM for semantic understanding + regex for broad pattern coverage
- **Automatic fallback**: Degrades gracefully when LM Studio is offline
- **Multi-language**: English primary, Spanish/Spanglish via LLM
- **Enterprise-ready**: Multi-layer safety gates prevent injection, leaks, and hallucinations
- **Convergence metrics**: Quantified distance-to-goal tracking via numpy gradient analysis
- **Certification suites**: 14 industrial scenarios + 5 adversarial chaos scenarios

---

## License

MIT — Copyright (c) 2026 Agustín Arellano. See `LICENSE` for details.
