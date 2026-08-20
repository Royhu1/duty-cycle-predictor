"""
SRF Platform Elevation API Client

Provides elevation data retrieval from the SRF (Sustainable Road Freight) platform.
API Documentation: https://data.csrf.ac.uk/
"""

import os
import logging
import requests
import numpy as np
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class SRFAPIClient:
    """Client for SRF elevation data API."""

    API_URL = "https://data.csrf.ac.uk/api/elevation"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize SRF API client.

        Args:
            api_key: SRF API key. If not provided, reads from SRF_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("SRF_API_KEY")
        if not self.api_key:
            logger.warning("SRF API key not provided. Elevation data will not be available.")

        self.session = requests.Session()

    def get_elevation_batch(
        self,
        coordinates: List[Tuple[float, float]],
        chunk_size: int = 1000,
        precision: int = 8,
    ) -> List[float]:
        """
        Batch retrieve elevation data from SRF API.

        Args:
            coordinates: List of (lat, lon) tuples
            chunk_size: Maximum points per API request (default: 1000)
            precision: Decimal places for coordinate precision (default: 8)

        Returns:
            List of elevation values in meters (np.nan for failed points)
        """
        if not coordinates:
            return []

        if not self.api_key:
            logger.warning("SRF API key not set. Returning NaN for all coordinates.")
            return [np.nan] * len(coordinates)

        elevations = []

        # Process in chunks
        for i in range(0, len(coordinates), chunk_size):
            chunk = coordinates[i : i + chunk_size]
            chunk_elevations = self._request_elevation(chunk, precision)
            elevations.extend(chunk_elevations)

        valid_count = sum(1 for e in elevations if not np.isnan(e))
        logger.info(f"SRF elevation: {valid_count}/{len(elevations)} valid points")

        return elevations

    def _request_elevation(
        self, coordinates: List[Tuple[float, float]], precision: int = 8
    ) -> List[float]:
        """
        Make a single API request for elevation data.

        Args:
            coordinates: List of (lat, lon) tuples
            precision: Decimal places for coordinates

        Returns:
            List of elevation values
        """
        # Format points as "lat,lon" strings
        points = [f"{lat:.{precision}f},{lon:.{precision}f}" for lat, lon in coordinates]

        # Prepare request data (form-urlencoded with multiple 'point' keys)
        data = [("point", p) for p in points]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            response = self.session.post(
                self.API_URL, headers=headers, data=data, timeout=30
            )

            if response.status_code == 200:
                return self._parse_response(response.json())
            else:
                logger.error(f"SRF API error: {response.status_code}, {response.text}")
                return [np.nan] * len(coordinates)

        except requests.exceptions.RequestException as e:
            logger.warning(f"SRF API request failed: {e}")
            return [np.nan] * len(coordinates)

    def _parse_response(self, data: list) -> List[float]:
        """
        Parse elevation data from API response.

        Args:
            data: API response data

        Returns:
            List of elevation values
        """
        elevations = []

        for point in data:
            if isinstance(point, dict) and "elevation" in point:
                elevations.append(float(point["elevation"]))
            elif isinstance(point, (int, float)):
                elevations.append(float(point))
            else:
                elevations.append(np.nan)

        return elevations

    @staticmethod
    def haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate the great circle distance between two points on Earth.

        Args:
            lat1, lon1: First point coordinates (degrees)
            lat2, lon2: Second point coordinates (degrees)

        Returns:
            Distance in meters
        """
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arcsin(np.sqrt(a))

        # Earth radius in meters
        r = 6371000
        return c * r
