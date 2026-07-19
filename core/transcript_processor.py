"""
core/transcript_processor.py — Procesador de Transcripciones Corporativas (V40.0).
Convierte texto libre de reuniones en artefactos de trabajo estructurados.
Soporta plantillas personalizadas desde el directorio templates/.
Sin conocimiento de dominio especifico — heuristicas universales de negocio.
"""
import re
import os
import string
from collections import defaultdict
from datetime import date


class TranscriptProcessor:
    """
    Analiza transcripciones de reuniones y extrae:
    - Action items con responsables y plazos
    - Dependencias entre tareas
    - Nivel de urgencia implicito
    - Estructura jerarquica (temas, subtemas, decisiones)
    """

    PATRON_ACCION = re.compile(
        r'(?P<owner>[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+'
        r'(?:will|shall|needs to|is responsible for|is going to|must|has to|commits to)\s+'
        r'(?P<action>.+?)(?:\.(?!\w)|!|\?|\n|$)',
        re.IGNORECASE
    )

    PATRON_TAREA = re.compile(
        r'(?:Action Item|Task|To[- ]?Do)\s*:\s*(?P<action>[^|]+?)'
        r'(?:\s*\|\s*(?:Assignee|Owner|Responsible)\s*:\s*(?P<owner>.+))?$',
        re.IGNORECASE | re.MULTILINE
    )

    DIAS = r'(?:Mon(?:day)?|Tue(?:sday)?|Wed(?:nesday)?|Thu(?:rsday)?|Fri(?:day)?|Sat(?:urday)?|Sun(?:day)?)'
    MESES = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'

    PATRON_FECHA = re.compile(
        r'(?:by|due|deadline|end of|before|EOD|COB|EOW)\s*:?\s*'
        r'(?P<fecha>(?:' + DIAS + r'|' + MESES + r'(?:\s\d{1,2})?(?:,?\s\d{4})?|'
        r'\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|'
        r'tomorrow|today|tonight|EOD|COB|EOW|this week|next week))',
        re.IGNORECASE
    )

    PATRON_URGENCIA = re.compile(
        r'\b(?:urgent|ASAP|critical|high priority|blocker|immediately|time-sensitive|P0|P1)\b',
        re.IGNORECASE
    )

    PATRON_ANUNCIO = re.compile(
        r'(?:IMPORTANT|URGENT|NOTE|REMINDER|ACTION|ATTENTION)\s*:.*?'
        r'(?P<action>.+?)\s+by\s+(?P<owner>[A-Z][a-z]+)'
        r'(?:.*?(?:deadline|by|due|before)\s*:?\s*(?P<deadline>.+?))?$',
        re.IGNORECASE | re.MULTILINE
    )

    PATRON_DEPENDENCIA = re.compile(
        r'(?:depends on|blocked by|waiting on|prerequisite|requires|needs|after)\s+'
        r'(?P<dependencia>[A-Z][^.,!?]+)',
        re.IGNORECASE
    )

    @staticmethod
    def extract_action_items(transcript_text: str) -> list[dict]:
        items = []
        lines = transcript_text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            for pattern in [TranscriptProcessor.PATRON_ACCION,
                            TranscriptProcessor.PATRON_TAREA,
                            TranscriptProcessor.PATRON_ANUNCIO]:
                match = pattern.search(line)
                if match:
                    data = match.groupdict()
                    owner = (data.get("owner") or "Unassigned").strip()
                    action = (data.get("action") or "").strip()

                    if TranscriptProcessor._es_valido(owner, action):
                        deadline = TranscriptProcessor._extraer_fecha(line)
                        urgencia = TranscriptProcessor._evaluar_urgencia(line)
                        dependencias = TranscriptProcessor._extraer_dependencias(line)

                        items.append({
                            "responsable": owner,
                            "accion": action,
                            "deadline": deadline or "No especificado",
                            "urgencia": urgencia,
                            "dependencias": dependencias,
                            "completado": False,
                            "linea_origen": line[:80],
                        })

        return TranscriptProcessor._deduplicar(items)

    @staticmethod
    def _es_valido(owner: str, action: str) -> bool:
        if len(action) < 5:
            return False
        if owner.lower() in action.lower():
            return False
        return True

    @staticmethod
    def _extraer_fecha(line: str) -> str | None:
        match = TranscriptProcessor.PATRON_FECHA.search(line)
        return match.group("fecha") if match else None

    @staticmethod
    def _evaluar_urgencia(line: str) -> str:
        if TranscriptProcessor.PATRON_URGENCIA.search(line):
            return "alta"
        return "normal"

    @staticmethod
    def _extraer_dependencias(line: str) -> list[str]:
        return [m.group("dependencia").strip()
                for m in TranscriptProcessor.PATRON_DEPENDENCIA.finditer(line)]

    @staticmethod
    def _deduplicar(items: list[dict]) -> list[dict]:
        vistos = set()
        unicos = []
        for item in items:
            clave = (item["accion"].lower(), item["responsable"].lower())
            if clave not in vistos:
                vistos.add(clave)
                unicos.append(item)
        return unicos

    @staticmethod
    def build_artifact(items: list[dict], artifact_type: str = "minutes") -> str:
        template_path = TranscriptProcessor._template_path(artifact_type)
        if os.path.exists(template_path):
            return TranscriptProcessor._render_template(template_path, items)
        return TranscriptProcessor._build_default(items, artifact_type)

    @staticmethod
    def _build_default(items: list[dict], artifact_type: str) -> str:
        if artifact_type == "project_plan":
            return TranscriptProcessor._build_project_plan(items)
        elif artifact_type == "prd":
            return TranscriptProcessor._build_prd(items)
        else:
            return TranscriptProcessor._build_minutes(items)

    @staticmethod
    def _template_path(template_name: str) -> str:
        base = os.path.join(os.path.dirname(__file__), "..", "templates")
        return os.path.normpath(os.path.join(base, f"{template_name}.md"))

    @staticmethod
    def _render_template(template_path: str, items: list[dict]) -> str:
        with open(template_path, encoding="utf-8") as f:
            tpl = f.read()
        context = TranscriptProcessor._build_context(items)
        return string.Template(tpl).safe_substitute(context)

    @staticmethod
    def _build_context(items: list[dict]) -> dict:
        by_owner = defaultdict(list)
        for it in items:
            by_owner[it["responsable"]].append(it)

        items_list = "\n".join(
            f"{i}. **{it['accion']}** — {it['responsable']} (vence: {it['deadline']})"
            for i, it in enumerate(items, 1)
        )

        items_by_owner_list = []
        for owner, tasks in sorted(by_owner.items()):
            items_by_owner_list.append(f"### {owner}")
            for t in tasks:
                items_by_owner_list.append(
                    f"- [ ] {t['accion']} (Deadline: {t['deadline']})"
                )
            items_by_owner_list.append("")
        items_by_owner = "\n".join(items_by_owner_list)

        deps_lines = []
        for it in items:
            if it.get("dependencias"):
                deps_lines.append(
                    f"- {it['accion']} depende de: {', '.join(it['dependencias'])}"
                )
        dependencies_section = "\n".join(deps_lines) if deps_lines else "Sin dependencias identificadas."

        timeline = "\n".join(
            f"- {it['accion']} → {it['deadline']}"
            for it in items if it['deadline'] != "No especificado"
        ) or "Plazos no especificados."

        deadlines = [it['deadline'] for it in items
                     if it['deadline'] != "No especificado"]
        completed = [it for it in items if it.get('completado')]
        pending = [it for it in items if not it.get('completado')]

        return {
            "date": str(date.today()),
            "items_list": items_list,
            "items_by_owner": items_by_owner,
            "dependencies_section": dependencies_section,
            "timeline": timeline,
            "meeting_type": "Reunion de Equipo",
            "attendees": ", ".join(sorted(set(it["responsable"] for it in items))),
            "topics": "Extraccion automatica de transcripcion.",
            "decisions": "Documentadas en los action items.",
            "next_meeting": "Por definir.",
            "objective": "Completar las tareas asignadas en la reunion.",
            "acceptance_criteria": (
                "- Cada accion debe tener un entregable verificable\n"
                "- Todo deadline debe ser explicito\n"
                "- Las dependencias deben estar resueltas antes del cierre"
            ),
            "completion_rate": f"{len(completed)}/{len(items)}" if items else "0/0",
            "avg_execution_time": "Por medir.",
            "extraction_accuracy": "Validada por Agetia 3 V40.",
            "exclusions": "Sin exclusiones documentadas.",
            "scope": "Transcripcion completa de la reunion.",
            "vulnerabilities": "Identificadas durante la reunion.",
            "residual_risks": "Documentados en las dependencias.",
            "next_audit": "Por programar.",
            "status_summary": "En progreso.",
            "key_points": items_list,
            "recommendations": "Dar seguimiento a cada action item antes de la proxima reunion.",
            "next_steps": "Completar las tareas asignadas.",
            "project_name": "Proyecto Agetia 3",
            "risk_matrix": "\n".join(
                f"| {it['accion'][:30]} | Media | Media | Medio | {it['responsable']} |"
                for it in items
            ) or "| — | — | — | — | — |",
            "accepted_risks": "Riesgos aceptados segun criterio del equipo.",
            "contingency_plan": "Reasignacion de tareas si es necesario.",
            "follow_up": "Proxima revision en reunion de seguimiento.",
            "sprint_name": "Sprint Actual",
            "sprint_summary": f"{len(items)} tareas identificadas.",
            "completed_items": "\n".join(
                f"- [x] {it['accion']}" for it in completed
            ) or "Ninguna tarea completada aun.",
            "blockers": dependencies_section,
            "went_well": "Extraccion automatica de action items.",
            "improvements": "Mejorar deteccion de plazos implicitos.",
            "action_items_retro": items_list,
            "velocity": f"{len(items)} tareas por sprint.",
        }

    @staticmethod
    def _build_minutes(items: list[dict]) -> str:
        lines = ["# Minuta de Reunion", "", "## Action Items", ""]
        for i, item in enumerate(items, 1):
            lines.append(f"{i}. **{item['accion']}**")
            lines.append(f"   - Responsable: {item['responsable']}")
            lines.append(f"   - Deadline: {item['deadline']}")
            lines.append(f"   - Urgencia: {item['urgencia']}")
            if item.get("dependencias"):
                lines.append(f"   - Dependencias: {', '.join(item['dependencias'])}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _build_project_plan(items: list[dict]) -> str:
        by_owner = defaultdict(list)
        for item in items:
            by_owner[item["responsable"]].append(item)
        lines = ["# Plan de Proyecto", "", "## Asignaciones por Responsable", ""]
        for owner, tasks in sorted(by_owner.items()):
            lines.append(f"### {owner}")
            for t in tasks:
                lines.append(f"- [ ] {t['accion']} (Deadline: {t['deadline']})")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _build_prd(items: list[dict]) -> str:
        lines = [
            "# PRD — Product Requirements Document",
            "",
            "## Requerimientos Funcionales",
            "",
        ]
        for item in items:
            lines.append(f"- **{item['accion']}**")
            lines.append(f"  - Owner: {item['responsable']} | Deadline: {item['deadline']}")
            lines.append("")
        lines.extend([
            "## Criterios de Aceptacion",
            "- Cada accion debe tener un entregable verificable",
            "- Todo deadline debe tener una fecha explicita",
            "- Las dependencias deben estar resueltas antes del cierre",
        ])
        return "\n".join(lines)
