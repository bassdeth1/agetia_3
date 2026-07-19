"""
core/safety_gate.py — Cortafuegos de Seguridad Estructural (V34.0 Skill Lift).
Intercepta tokens de salida y acciones propuestas antes de enviarlos al entorno.
Valida contra patrones bloqueados, confina al espacio de accion disponible,
y fuerza fallback seguro. Alineado con ClawsBench safety paradigm.
Sin conocimiento de dominio.
"""
import os
import re


class SafetyGate:
    """
    Cortafuegos de Seguridad e Inmutabilidad de Agetia 2.
    Sin conocimiento de dominio. Solo restricciones estructurales universales.
    """

    # Patrones de seguridad por nivel de riesgo
    CRITICAL_PATTERNS = [
        "exit", "quit", "shutdown", "reboot", "halt",
    ]

    DESTRUCTIVE_PATTERNS = [
        "remove(", "unlink(", "rmdir(", "shutil.rmtree",
        "os.remove", "os.unlink", "os.rmdir",
    ]

    PERMISSION_PATTERNS = [
        "chmod", "chown", "sudo", "su",
    ]

    CODE_EXEC_PATTERNS = [
        "__import__", "eval(", "exec(", "compile(",
    ]

    NETWORK_PATTERNS = [
        "import socket", "import requests",
        "import urllib", "import http",
    ]

    BLOCKED_PATTERNS = (
        CRITICAL_PATTERNS + DESTRUCTIVE_PATTERNS + PERMISSION_PATTERNS
        + CODE_EXEC_PATTERNS + NETWORK_PATTERNS
    )

    @staticmethod
    def validate(token: str, available_tokens: list[str]) -> tuple[bool, str]:
        """
        Valida que el token elegido sea seguro y este en el espacio de acciones.
        Retorna (aprobado: bool, mensaje: str).
        """
        if not token:
            return False, "Token vacio: no se puede ejecutar una accion nula."

        if token not in available_tokens:
            return False, (
                f"Token '{token}' no esta en el conjunto de acciones disponibles "
                f"{available_tokens}. Accion fuera de limites del espacio de estado."
            )

        for pattern in SafetyGate.BLOCKED_PATTERNS:
            if pattern in token.lower():
                return False, (
                    f"Token '{token}' contiene el patron bloqueado '{pattern}'. "
                    f"Violacion de seguridad estructural de nivel critico."
                )

        return True, "Token validado y seguro."

    @staticmethod
    def force_safe_fallback(token: str, available_tokens: list[str],
                            default_token: str = None) -> tuple[str, str]:
        """
        Fuerza la sustitucion de un token inseguro por la primera alternativa
        disponible, o por un valor por defecto.
        Retorna (token_final: str, alerta: str).
        """
        approved, msg = SafetyGate.validate(token, available_tokens)
        if approved:
            return token, ""

        fallback = default_token or (available_tokens[0] if available_tokens else "NO_ACTION")
        alerta = (
            f"[SAFETY GATE] Token '{token}' rechazado: {msg} "
            f"Forzando fallback a '{fallback}'."
        )
        return fallback, alerta

    @staticmethod
    def validate_skill_instructions(skill_path: str) -> list[dict]:
        """
        Escanea un SKILL.md en busca de instrucciones que podrian violar
        la seguridad estructural. Usa limites de palabra para evitar falsos positivos.
        Omite bloques de codigo y lineas con patrones entre backticks (documentacion).
        Retorna lista de violaciones encontradas.
        """
        violations = []
        if not os.path.exists(skill_path):
            return [{"tipo": "error", "detalle": f"Archivo no encontrado: {skill_path}"}]

        with open(skill_path, "r") as f:
            content = f.read()

            in_code_block = False
        for i, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            lower = line.lower()
            lower_no_backtick = re.sub(r'`[^`]*`', '', lower)
            for pattern in SafetyGate.BLOCKED_PATTERNS:
                escaped = re.escape(pattern)
                regex = rf'\b{escaped}\b' if pattern.isalpha() else escaped
                if re.search(regex, lower_no_backtick):
                    violations.append({
                        "linea": i,
                        "patron": pattern,
                        "contenido": line.strip(),
                        "severidad": "CRITICAL" if pattern in SafetyGate.CRITICAL_PATTERNS else "HIGH",
                    })
        return violations

    @staticmethod
    def get_risk_assessment(action_description: str) -> dict:
        """
        Evalua el nivel de riesgo de una descripcion de accion.
        Retorna un dict con nivel de riesgo y patrones coincidentes.
        """
        matched = []
        for pattern in SafetyGate.BLOCKED_PATTERNS:
            if pattern in action_description.lower():
                matched.append(pattern)

        if not matched:
            return {"riesgo": "bajo", "patrones_coincidentes": []}

        has_critical = any(p in SafetyGate.CRITICAL_PATTERNS for p in matched)
        has_destructive = any(p in SafetyGate.DESTRUCTIVE_PATTERNS for p in matched)

        if has_critical:
            nivel = "CRITICAL"
        elif has_destructive:
            nivel = "ALTO"
        else:
            nivel = "MEDIO"

        return {"riesgo": nivel, "patrones_coincidentes": matched}
