"""
core/timeline_memory.py — Memoria de Linea Temporal V30.0

Acumula el historial cronologico completo de estados y acciones
para inyectarlo en el prompt del modelo como In-Context Learning
travectorial. Aprovecha los 180k de contexto activo de LM Studio.

Sin conocimiento de dominio. Sin parches ARC ni Pokemon.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import numpy as np


@dataclass
class TimelineEntry:
    step: int
    action_id: Optional[int]
    entity_summary: str
    grid_shape: tuple
    grid_hash: int
    changed: bool
    n_entities: int
    n_unique_values: int


class TimelineMemory:
    """
    Acumulador cronologico de estados/acciones.

    Almacena hasta `max_entries` entradas y produce un texto
    de linea temporal para inyectar en el prompt del modelo.
    """

    def __init__(self, max_entries: int = 40):
        self.max_entries = max_entries
        self._entries: List[TimelineEntry] = []
        self._first_entry: Optional[TimelineEntry] = None

    def reset(self):
        self._entries.clear()
        self._first_entry = None

    def push(self, step: int, action_id: Optional[int],
             entity_summary: str, grid_shape: tuple,
             grid_hash: int, changed: bool,
             n_entities: int, n_unique_values: int) -> TimelineEntry:
        entry = TimelineEntry(
            step=step, action_id=action_id,
            entity_summary=entity_summary, grid_shape=grid_shape,
            grid_hash=grid_hash, changed=changed,
            n_entities=n_entities, n_unique_values=n_unique_values,
        )
        if self._first_entry is None:
            self._first_entry = entry
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries.pop(0)
        return entry

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> List[TimelineEntry]:
        return list(self._entries)

    def build_timeline_text(self, include_first: bool = True) -> str:
        """
        Construye el texto de linea temporal para inyectar en el prompt.

        Formato cronologico: cada entrada muestra paso, accion,
        cambio detectado, entidades presentes y resumen de entidades.
        """
        if not self._entries:
            return ""

        lines = ["\n--- LINEA TEMPORAL (historial completo) ---"]

        entries = list(self._entries)
        if include_first and self._first_entry and self._first_entry not in entries:
            entries.insert(0, self._first_entry)

        for e in entries:
            action_str = f"Accion={e.action_id}" if e.action_id is not None else "Accion=ninguna"
            change_str = "CAMBIO" if e.changed else "sin cambio"
            parts = [
                f"  #{e.step}:",
                action_str,
                f"grid={e.grid_shape[0]}x{e.grid_shape[1]}",
                f"hash={e.grid_hash & 0xFFFF:04x}",
                change_str,
                f"entidades={e.n_entities}",
                f"valores={e.n_unique_values}",
            ]
            lines.append(" ".join(parts))

        return "\n".join(lines)

    def build_detailed_timeline(self, include_entity_maps: bool = True) -> str:
        """
        Linea temporal extendida con mapas de entidades completos.
        (usa mas tokens pero expone mas informacion al modelo)
        """
        if not self._entries:
            return ""

        lines = ["\n--- LINEA TEMPORAL DETALLADA ---"]

        for e in self._entries:
            action_str = f"Accion={e.action_id}" if e.action_id is not None else "Inicial"
            change_str = "CAMBIO" if e.changed else "sin cambio"
            header = f"  Paso {e.step} | {action_str} | {change_str}"
            lines.append(header)
            if include_entity_maps and e.entity_summary:
                for el in e.entity_summary.split("\n"):
                    lines.append("    " + el)

        return "\n".join(lines)

    def get_action_history(self) -> List[int]:
        """Historial de acciones ejecutadas (para analisis de patrones)."""
        return [e.action_id for e in self._entries if e.action_id is not None]

    def get_steps_since_change(self) -> int:
        """Pasos desde el ultimo cambio detectado."""
        for i in range(len(self._entries) - 1, -1, -1):
            if self._entries[i].changed:
                return len(self._entries) - 1 - i
        return len(self._entries)

    def get_repeated_actions(self, window: int = 5) -> List[int]:
        """Acciones repetidas en la ultima ventana."""
        recent = self.get_action_history()[-window:]
        if len(recent) < window:
            return []
        from collections import Counter
        return [a for a, c in Counter(recent).items() if c >= 3]
