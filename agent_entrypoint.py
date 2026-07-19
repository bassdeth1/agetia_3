"""
agent_entrypoint.py — Punto de Entrada Híbrido V40.0.
Combina LLM semantico (LM Studio) + regex deterministico con fallback automatico.
Contract:
  Input:  { "transcript": str, "task": str, "expected_format": str }
  Output: { "status": str, "artifact": str, "metrics": dict, "source": str }
"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.transcript_processor import TranscriptProcessor
from core.enterprise_safety import EnterpriseSafetyGate
from core.llm_semantic_analyzer import LLMSemanticAnalyzer
from core.convergence_core import ConvergenceCore


def handle_sitrep_request_v40(payload: dict) -> dict:
    transcript = payload.get("transcript", "")
    task_assigned = payload.get("task", "")
    artifact_type = payload.get("expected_format", "project_plan")

    print(f"\n[AGETIA 3 V40] Task: '{task_assigned}' | Format: {artifact_type}")
    print(f"[AGETIA 3 V40] Transcript: {len(transcript)} chars")

    analyzer = LLMSemanticAnalyzer()

    cognitive_report = analyzer.analyze_transcript(transcript)
    source = cognitive_report.get("source", "unknown")
    print(f"  Source: {source}")

    if not cognitive_report.get("is_safe", True):
        reason = cognitive_report.get("safety_reason", "Unknown threat")
        print(f"  [BIO-SHIELD ACTIVATED] {reason}")
        return {
            "status": "REJECTED",
            "error": f"Security Exception: {reason}",
            "source": source,
        }

    llm_items = cognitive_report.get("action_items", [])
    print(f"  Items extracted: {len(llm_items)}")

    deterministic_items = TranscriptProcessor.extract_action_items(transcript)
    if llm_items:
        final_items = llm_items
        print(f"  Using LLM items ({len(llm_items)})")
    else:
        final_items = [
            {"owner": it["responsable"], "action": it["accion"],
             "deadline": it["deadline"]}
            for it in deterministic_items
        ]
        print(f"  Using deterministic fallback ({len(final_items)} items)")

    if not final_items:
        print("  [WARN] No action items extracted — generating empty artifact")
        artifact = f"# {artifact_type.replace('_', ' ').title()}\n\nNo action items were identified in the transcript."
    else:
        dedup_items = _dedup_items(final_items)
        valid_items = _validate_with_llm(dedup_items, transcript, analyzer)
        artifact = TranscriptProcessor.build_artifact(
            [_to_transcript_item(it) for it in valid_items],
            artifact_type,
        )

    artifact_violations = EnterpriseSafetyGate.validate_enterprise_output(artifact)
    if artifact_violations:
        print(f"  [DATA LEAK BLOCKED] {len(artifact_violations)} violations in output")
        return {
            "status": "REJECTED",
            "error": f"Data leak blocked: {len(artifact_violations)} violations",
            "violations": artifact_violations,
            "source": source,
        }

    history = [float(i) / max(len(final_items), 1) for i in range(len(final_items) + 1)]
    gradient = ConvergenceCore.calculate_system_gradient(
        current_metric=float(len(final_items)),
        target_metric=float(max(len(final_items), 1)),
        history_metrics=history,
    )

    print(f"  [COMPLETE] Artifact: {len(artifact)} chars | "
          f"Convergence: {gradient['tendencia']}")

    return {
        "status": "SUCCESS",
        "artifact": artifact,
        "source": source,
        "metrics": {
            "items_extracted": len(final_items),
            "artifact_length_chars": len(artifact),
            "artifact_type": artifact_type,
            "convergence": gradient,
        },
    }


def _dedup_items(items: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for it in items:
        key = (it.get("action", "").lower().strip(),
               it.get("owner", "").lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique


def _validate_with_llm(items: list[dict], transcript: str,
                        analyzer: LLMSemanticAnalyzer) -> list[dict]:
    validated = []
    for it in items:
        confidence = analyzer.validate_action_item(it, transcript)
        if confidence >= 0.3:
            validated.append(it)
        else:
            print(f"  [LLM REJECTED] '{it.get('action', '')[:40]}' "
                  f"(confidence: {confidence:.2f})")
    return validated or items


def _to_transcript_item(it: dict) -> dict:
    return {
        "responsable": it.get("owner", "Unassigned"),
        "accion": it.get("action", ""),
        "deadline": it.get("deadline", "No especificado"),
        "urgencia": "normal",
        "dependencias": [],
        "completado": False,
    }


if __name__ == "__main__":
    test_payload = {
        "transcript": (
            "Q3 Planning — July 18 2026\n\n"
            "Alice will finalize the budget by Friday.\n"
            "Bob needs to update the API docs before the release.\n"
            "Carol is responsible for the security audit.\n"
            "Action Item: Deploy staging | Assignee: David\n"
            "Task: Write integration tests | Owner: Eve\n"
        ),
        "task": "Generate project plan",
        "expected_format": "project_plan",
    }

    result = handle_sitrep_request_v40(test_payload)
    print(f"\n{'='*50}")
    print(f"STATUS: {result['status']} | Source: {result.get('source', 'N/A')}")
    if result["status"] == "SUCCESS":
        print(f"\n--- ARTIFACT ({result['metrics']['artifact_type']}) ---")
        print(result["artifact"])
