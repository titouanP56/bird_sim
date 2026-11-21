"""Optional GIS raster loader and alignment utilities (EPSG:2154, 10 m master grid).

Requires the optional ``[gis]`` dependency group (``rasterio``, ``xarray``) at
runtime when reading real RGE ALTI and OSO Theia rasters.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


class GISLoader:
    """Loader and spatial aligner for RGE ALTI (5 m) and OSO Theia (10 m) rasters.

    Enforces ``EPSG:2154`` projection, checks ``AREA_OR_POINT`` GeoTIFF pixel
    registration (``GTRasterTypeGeoKey``) before computing topographic gradients,
    and prepares ``float32`` / ``uint8`` arrays for in-RAM O(1) lookup (ADR-02).
    """

    def __init__(self, target_crs: str = "EPSG:2154", master_resolution_m: float = 10.0) -> None:
        """Initialize the GIS loader with target projection and resolution.

        Args:
            target_crs: Target projected coordinate reference system (default ``EPSG:2154``).
            master_resolution_m: Master grid pixel spacing in meters (default ``10.0``).
        """
        raise NotImplementedError

    def load_dem_and_derivatives(
        self, dem_path: str | Path
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Load 5 m RGE ALTI DEM, compute 3x3 slope/aspect, and bilinearly resample to 10 m.

        Verifies ``AREA_OR_POINT`` registration and applies a half-pixel shift
        when aligning ``RasterPixelIsArea`` with ``RasterPixelIsPoint`` grids.

        Args:
            dem_path: Path to the input GeoTIFF digital elevation model.

        Returns:
            Tuple ``(elevation_m, slope_rad, aspect_rad)`` as ``float32`` 2D arrays.
        """
        raise NotImplementedError

    def load_land_cover_oso(
        self, oso_path: str | Path, reference_shape: tuple[int, int]
    ) -> np.ndarray:
        """Load 10 m OSO Theia land-cover raster via strict nearest-neighbor alignment.

        Args:
            oso_path: Path to the OSO Theia categorical raster.
            reference_shape: Expected ``(height, width)`` of the master 10 m grid.

        Returns:
            2D ``uint8`` array encoding the 6 ecological facies identifiers.
        """
        raise NotImplementedError

    def compute_shrub_cover_20m_grid(self, canopy_fraction_grid: np.ndarray) -> np.ndarray:
        """Compute local 20 m shrub/canopy cover (%) via 2-pixel circular convolution.

        Args:
            canopy_fraction_grid: 2D ``float32`` array of per-cell shrub/tree cover in ``[0, 1]``.

        Returns:
            2D ``float32`` array of mean canopy cover in ``[0.0, 100.0]`` over a 20 m radius.
        """
        raise NotImplementedError

    def world_to_grid_index(
        self,
        x: float,
        y: float,
        xmin: float,
        ymax: float,
        resolution_m: float,
    ) -> tuple[int, int]:
        """Convert projected coordinates ``(x, y)`` in meters to ``(row, col)`` in O(1).

        Args:
            x: Easting coordinate in meters (EPSG:2154).
            y: Northing coordinate in meters (EPSG:2154).
            xmin: Western bound of the master grid in meters.
            ymax: Northern bound of the master grid in meters.
            resolution_m: Pixel size in meters.

        Returns:
            Grid indices ``(row, col)``.
        """
        raise NotImplementedError
