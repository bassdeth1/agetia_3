"""
core/convergence_core.py — Calculador de Distancia al Objetivo V34.0

Mide la tasa de exito o aproximacion al objetivo sin importar la competencia.
Agnostico: opera sobre cualquier metrica escalar que represente el grado de
completitud del sistema (niveles, puntuacion, masa activa, etc.).
"""
import numpy as np
from typing import List, Optional


class ConvergenceCore:
    """
    Núcleo de Convergencia de Agetia 2.
    Calcula el gradiente de aproximacion al estado de exito.
    Sin conocimiento de dominio. Solo aritmetica de sistemas dinamicos.
    """

    @staticmethod
    def calculate_system_gradient(
        current_metric: float,
        target_metric: float = 1.0,
        history_metrics: Optional[List[float]] = None,
    ) -> dict:
        """
        Calcula el gradiente de aproximacion al estado de exito.

        Args:
            current_metric: Valor actual del sistema (ej: 0.0 = 0% completado).
            target_metric: Valor objetivo (default 1.0 = 100%).
            history_metrics: Serie temporal de metricas anteriores.

        Returns:
            Dict con distancia, velocidad, aceleracion, estado de estabilizacion.
        """
        if history_metrics is None:
            history_metrics = []

        # Distancia cruda al objetivo (error residual)
        distance = target_metric - current_metric
        distance = max(0.0, distance)  # no negativa

        # Velocidad de convergencia (primera derivada)
        velocity = 0.0
        if len(history_metrics) >= 2:
            velocity = history_metrics[-1] - history_metrics[-2]
        elif len(history_metrics) == 1 and len(history_metrics) < 2:
            velocity = current_metric - history_metrics[-1]

        # Aceleracion de convergencia (segunda derivada)
        acceleration = 0.0
        if len(history_metrics) >= 3:
            v1 = history_metrics[-1] - history_metrics[-2]
            v2 = history_metrics[-2] - history_metrics[-3]
            acceleration = v1 - v2

        # Tasa de completitud relativa
        completion_pct = (
            (current_metric / target_metric * 100.0)
            if target_metric > 0
            else 0.0
        )

        # Estado de estabilizacion
        stabilized = abs(distance) < 1e-6

        # Direccion de la tendencia
        if velocity > 0.001:
            trend = "acercandose al objetivo"
        elif velocity < -0.001:
            trend = "alejandose del objetivo"
        else:
            trend = "estancado"

        return {
            "distancia_objetivo": round(distance, 4),
            "completitud_pct": round(completion_pct, 2),
            "velocidad_convergencia": round(velocity, 4),
            "aceleracion_convergencia": round(acceleration, 4),
            "tendencia": trend,
            "estado_estabilizado": stabilized,
            "target": target_metric,
            "current": current_metric,
        }

    @staticmethod
    def compute_action_efficiency(
        action_id: int,
        pre_action_distance: float,
        post_action_distance: float,
    ) -> dict:
        """
        Evalua la eficiencia de una accion para reducir la distancia al objetivo.
        Retorna el delta y la eficiencia relativa.
        """
        delta = pre_action_distance - post_action_distance
        efficiency_pct = 0.0
        if pre_action_distance > 0:
            efficiency_pct = (delta / pre_action_distance) * 100.0
        return {
            "action_id": action_id,
            "delta_distancia": round(delta, 4),
            "eficiencia_pct": round(efficiency_pct, 2),
            "mejora": delta > 0,
            "empeora": delta < 0,
        }

    @staticmethod
    def infer_target_metric(trajectory_metrics: List[float]) -> float:
        """
        Infiere cual podria ser la metrica objetivo analizando la trayectoria.
        Si las metricas convergen a un valor estable, ese es el objetivo inferido.
        Si siempre suben, el maximo local es el mejor candidato.
        """
        if not trajectory_metrics:
            return 1.0  # default universal

        arr = np.array(trajectory_metrics)
        # Si la serie tiene una meseta al final, ese es el objetivo
        if len(arr) >= 5:
            tail = arr[-5:]
            if np.std(tail) < 0.01:
                return float(tail[-1])
        # Si la tendencia es monotonicamente creciente, objetivo = max
        if len(arr) >= 3 and all(arr[i] <= arr[i + 1] for i in range(len(arr) - 1)):
            return float(arr[-1])
        # Fallback: el maximo observado
        return float(max(arr))

    @staticmethod
    def build_gradient_report(gradient: dict) -> str:
        """Convierte el gradiente en texto legible para el prompt."""
        return (
            f"GRADIENTE_OBJETIVO: distancia={gradient['distancia_objetivo']} "
            f"completitud={gradient['completitud_pct']}% "
            f"velocidad={gradient['velocidad_convergencia']} "
            f"tendencia={gradient['tendencia']}"
        )
