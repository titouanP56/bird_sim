"""Parquet and CSV exporters for simulation telemetry and daily GPS-validation summaries."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from bonelli_ibm.core.types import AgentTelemetry


class SimulationExporter:
    """Exporter converting ``AgentTelemetry`` trajectories to Parquet and CSV (ADR-04).

    Parquet (backed by ``pyarrow``) is the primary format for full annual
    runs (~105,120 steps/bird/year); CSV is provided for small debugging runs.
    """

    def __init__(self, output_dir: str | Path) -> None:
        """Initialize the exporter targeting ``output_dir``.

        Args:
            output_dir: Directory where Parquet/CSV output files will be written.
        """
        raise NotImplementedError

    def telemetry_to_dataframe(self, records: Sequence[AgentTelemetry]) -> pd.DataFrame:
        """Convert a sequence of ``AgentTelemetry`` snapshots into a typed DataFrame.

        Args:
            records: Sequence of immutable telemetry records.

        Returns:
            Pandas DataFrame with columns matching ``AgentTelemetry`` fields.
        """
        raise NotImplementedError

    def export_telemetry_parquet(
        self,
        records: Sequence[AgentTelemetry],
        filename: str = "telemetry.parquet",
    ) -> Path:
        """Write full trajectory telemetry to a compressed Parquet file.

        Args:
            records: Sequence of ``AgentTelemetry`` snapshots.
            filename: Output filename inside ``output_dir``.

        Returns:
            Path to the written Parquet file.
        """
        raise NotImplementedError

    def export_telemetry_csv(
        self,
        records: Sequence[AgentTelemetry],
        filename: str = "telemetry.csv",
    ) -> Path:
        """Write trajectory telemetry to a CSV file (debugging / small runs).

        Args:
            records: Sequence of ``AgentTelemetry`` snapshots.
            filename: Output filename inside ``output_dir``.

        Returns:
            Path to the written CSV file.
        """
        raise NotImplementedError

    def export_daily_summary_parquet(
        self,
        records: Sequence[AgentTelemetry],
        filename: str = "daily_summary.parquet",
    ) -> Path:
        """Aggregate and export daily metrics (``tau_flight``, ``R_day``, ``St_day``, ``ODBA``).

        Produces a compact table ready for comparison against
        ``docs/01_Modele/species/Aigle de Bonelli/Cibles_Validation_GPS.md``.

        Args:
            records: Sequence of ``AgentTelemetry`` snapshots.
            filename: Output filename inside ``output_dir``.

        Returns:
            Path to the written Parquet file.
        """
        raise NotImplementedError
