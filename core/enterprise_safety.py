"""
core/enterprise_safety.py — Cortafuegos de Seguridad Empresarial (V39.0 SitRep).
Extiende SafetyGate con patrones de riesgo corporativo:
- Inyeccion de prompts desde transcripciones
- Exfiltracion de datos sensibles
- Alucinacion de action items ficticios
- Vulneracion de confidencialidad
"""
import re
import sys
sys.path.insert(0, ".")
from core.safety_gate import SafetyGate


class EnterpriseSafetyGate(SafetyGate):
    """
    Capa de seguridad corporativa sobre SafetyGate.
    Sin conocimiento de dominio especifico — solo restricciones
    estructurales universales del entorno empresarial.
    """

    # Patrones de inyeccion de prompts desde transcripciones
    INJECTION_PATTERNS = [
        "ignore previous instructions",
        "ignore all instructions",
        "forget your instructions",
        "override system prompt",
        "you are now",
        "act as if",
        "pretend to be",
        "do not follow",
        "disregard",
        "NEW INSTRUCTIONS",
        "SYSTEM OVERRIDE",
        "from now on",
    ]

    # Patrones de datos confidenciales
    CONFIDENTIAL_PATTERNS = [
        "password",
        "credentials",
        "api_key",
        "secret",
        "token",
        "confidential",
        "classified",
        "internal only",
        "privileged",
        "attorney-client",
        "NDA",
        "trade secret",
        "proprietary",
    ]

    # Patrones de exfiltracion empresarial
    EXFILTRATION_PATTERNS = [
        "send to",
        "forward to",
        "post to",
        "upload to",
        "export to",
        "email to",
        "share with",
        "make public",
        "publish",
    ]

    # Patrones de alucinacion (afirmaciones sin respaldo en la transcripcion)
    HALLUCINATION_PATTERNS = [
        "presumably",
        "probably",
        "might have",
        "could be",
        "assume that",
        "we think",
        "it seems",
        "apparently",
    ]

    ENTERPRISE_BLOCKED = (
        INJECTION_PATTERNS + CONFIDENTIAL_PATTERNS
        + EXFILTRATION_PATTERNS + HALLUCINATION_PATTERNS
    )

    @staticmethod
    def validate_enterprise_output(artifact_text: str) -> list[dict]:
        """
        Valida que un artefacto generado no contenga:
        - Instrucciones inyectadas desde la transcripcion
        - Datos confidenciales filtrados
        - Afirmaciones especulativas no respaldadas
        """
        violations = []
        for i, line in enumerate(artifact_text.split("\n"), 1):
            lower = line.lower()
            for pattern in EnterpriseSafetyGate.ENTERPRISE_BLOCKED:
                escaped = re.escape(pattern)
                regex = rf'\b{escaped}\b' if pattern.isalpha() else escaped
                if re.search(regex, lower):
                    violations.append({
                        "linea": i,
                        "patron": pattern,
                        "contenido": line.strip()[:100],
                        "tipo": "enterprise_risk",
                    })
        return violations

    @staticmethod
    def validate_transcript_safety(transcript_text: str) -> list[dict]:
        """
        Escanea la transcripcion entrante en busca de intentos de
        inyeccion de prompts ocultos en el texto de la reunion.
        """
        warnings = []
        for i, line in enumerate(transcript_text.split("\n"), 1):
            lower = line.lower()
            for pattern in EnterpriseSafetyGate.INJECTION_PATTERNS:
                if pattern in lower:
                    warnings.append({
                        "linea": i,
                        "tipo": "prompt_injection",
                        "patron": pattern,
                        "contenido": line.strip()[:100],
                        "severidad": "CRITICAL",
                    })
        return warnings

    @staticmethod
    def compute_confidence_score(action_item: dict, transcript_context: str) -> float:
        """
        Evalua que tan probable es que un action item extraido sea real
        (no una alucinacion). Retorna puntaje 0.0 - 1.0.
        """
        score = 1.0
        action = action_item.get("accion", "").lower()

        for pattern in EnterpriseSafetyGate.HALLUCINATION_PATTERNS:
            if pattern in action:
                score -= 0.3

        if action_item.get("responsable") == "Unassigned":
            score -= 0.2

        if not action_item.get("deadline") or action_item["deadline"] == "No especificado":
            score -= 0.1

        contexto_bajo = len(transcript_context.strip().split()) < 50
        if contexto_bajo:
            score -= 0.2

        return max(0.0, score)


class SitRepSafetyPipeline:
    """
    Pipeline completo de seguridad para el flujo SitRep:
    Transcripcion → Accion → Artefacto
    """

    @staticmethod
    def run(transcript: str, artifact_type: str = "minutes") -> dict:
        result = {
            "transcript_warnings": [],
            "artifact_violations": [],
            "passed": True,
        }

        transcript_warnings = EnterpriseSafetyGate.validate_transcript_safety(transcript)
        result["transcript_warnings"] = transcript_warnings
        if transcript_warnings:
            result["passed"] = False

        return result
