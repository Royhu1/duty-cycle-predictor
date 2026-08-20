"""
HERE Maps API client for routing and geocoding services.
"""

import requests
import pandas as pd
import flexpolyline
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)


class HereAPIClient:
    """Client for HERE Maps API services."""

    def __init__(self, api_key: str):
        """Initialize HERE API client.

        Args:
            api_key: HERE API key
        """
        self.api_key = api_key
        self.base_url = "https://router.hereapi.com/v8"
        self.session = requests.Session()

    def get_route_dataframe(self, origin, destination, via_points=None, departure_time=None, transport_mode='truck') -> pd.DataFrame:

        response = self._get_route_resp(
            origin=origin,
            destination=destination,
            via=via_points,
            departure_time=departure_time,
            transportMode=transport_mode,
        )

        route_df = self._resp2df(response)

        # 暂时注释掉 route_info 的构建，用不上
        # route_info = {
        #     "origin": {"lat": origin[0], "lon": origin[1]},
        #     "destination": {"lat": destination[0], "lon": destination[1]},
        #     "via_points": via_points or [],
        #     "departure_time": departure_time.isoformat(),
        #     "num_waypoints": len(route_df),
        # }

        # if "routes" in response and len(response["routes"]) > 0:
        #     route = response["routes"][0]
        #     if "sections" in route:
        #         total_distance = 0
        #         total_duration = 0
        #         for section in route["sections"]:
        #             if "summary" in section:
        #                 total_distance += section["summary"].get("length", 0)
        #                 total_duration += section["summary"].get("duration", 0)

        #         route_info["total_distance_m"] = total_distance
        #         route_info["total_duration_s"] = total_duration

        # logger.info(f"Route obtained: {len(route_df)} waypoints")

        return route_df#, route_info

    def _get_route_resp(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        via: Optional[List[Tuple[float, float]]] = None,
        passThrough: Optional[List[bool]] = None,
        departure_time: Optional[datetime] = None,
        transportMode: str = "car",
        avoid_features: Optional[List[str]] = None,
        traffic_mode: str = "enabled"
    ) -> Dict[str, Any]:
        """Get route response from HERE API.

        Args:
            origin: Origin coordinates (lat, lon)
            destination: Destination coordinates (lat, lon)
            via: List of via point coordinates
            passThrough: List of boolean flags for via points
            departure_time: Departure time for traffic-aware routing
            transportMode: Transport mode (car, truck, pedestrian, bicycle)
            avoid_features: Features to avoid (tollRoad, ferry, tunnel, etc.)
            traffic_mode: Traffic mode (enabled, disabled, historical)

        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}/routes"

        # Use list of tuples to support multiple 'via' parameters with same key
        params = [
            ("apikey", self.api_key),
            ("origin", f"{origin[0]},{origin[1]}"),
            ("destination", f"{destination[0]},{destination[1]}"),
            ("transportMode", transportMode),
            ("return", "summary,polyline,turnByTurnActions,actions"),
            ("spans", "names,speedLimit,maxSpeed,dynamicSpeedInfo,segmentId,segmentRef"),
            ("traffic", traffic_mode),
            ("routingMode", "fast"),
        ]

        # Add via points as separate parameters
        if via and len(via) > 0:
            for i, (lat, lon) in enumerate(via):
                via_value = f"{lat},{lon}"
                # Add passThrough flag if provided (format: lat,lon!passThrough=true)
                if passThrough and i < len(passThrough) and passThrough[i]:
                    via_value += "!passThrough=true"
                params.append(("via", via_value))

        # Add departure time if provided
        if departure_time:
            # Format as ISO 8601
            params.append(("departureTime", departure_time.strftime("%Y-%m-%dT%H:%M:%S")))

        # Add avoid features if provided
        if avoid_features:
            params.append(("avoid[features]", ",".join(avoid_features)))

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"HERE API request failed: {e}")
            raise

    def _resp2df(self, response: Dict[str, Any]) -> pd.DataFrame:
        """Convert HERE API route response to DataFrame.

        Args:
            response: HERE API response dictionary

        Returns:
            DataFrame with route waypoints and attributes
        """
        if "routes" not in response or len(response["routes"]) == 0:
            raise ValueError("No routes found in response")

        route = response["routes"][0]

        if "sections" not in route:
            raise ValueError("No sections found in route")

        # Initialize DataFrame with expected columns
        route_df = pd.DataFrame(columns=['Lat', 'Lon', 'Elev', 'MaxSpeed', 'TrafficSpeed', 'BaseSpeed', 'Action'])

        global_offset = 0  # Track offset across multiple sections
        num_sections = len(route["sections"])

        for section_idx, section in enumerate(route["sections"]):
            is_last_section = (section_idx == num_sections - 1)

            # 1. Extract polyline coordinates
            if "polyline" in section:
                coords = flexpolyline.decode(section["polyline"])
                for wp_idx, coord in enumerate(coords):
                    idx = global_offset + wp_idx
                    route_df.loc[idx, "Lat"] = coord[0]
                    route_df.loc[idx, "Lon"] = coord[1]
                    route_df.loc[idx, "Elev"] = coord[2] if len(coord) >= 3 else None

            # 2. Extract speed info from spans
            if "spans" in section:
                for span in section["spans"]:
                    span_offset = global_offset + span.get("offset", 0)
                    # MaxSpeed directly from span
                    if "maxSpeed" in span:
                        route_df.loc[span_offset, "MaxSpeed"] = span["maxSpeed"]
                    # TrafficSpeed and BaseSpeed from dynamicSpeedInfo
                    if "dynamicSpeedInfo" in span:
                        dsi = span["dynamicSpeedInfo"]
                        if "trafficSpeed" in dsi:
                            route_df.loc[span_offset, "TrafficSpeed"] = dsi["trafficSpeed"]
                        if "baseSpeed" in dsi:
                            route_df.loc[span_offset, "BaseSpeed"] = dsi["baseSpeed"]

            # 3. Extract actions from turnByTurnActions (preferred) or actions
            actions_key = "turnByTurnActions" if "turnByTurnActions" in section else "actions"
            if actions_key in section:
                for action_item in section[actions_key]:
                    action_offset = global_offset + action_item.get("offset", 0)
                    action_name = action_item.get("action")
                    # Rename intermediate 'arrive' to 'arrive_viapoint', keep only final 'arrive'
                    if action_name == "arrive" and not is_last_section:
                        action_name = "arrive_viapoint"
                    route_df.loc[action_offset, "Action"] = action_name

            # Update global offset for next section
            if "polyline" in section:
                global_offset += len(coords)

        # 4. Forward fill missing speed values
        route_df[['MaxSpeed', 'TrafficSpeed', 'BaseSpeed']] = (
            route_df[['MaxSpeed', 'TrafficSpeed', 'BaseSpeed']]
            .ffill()
            .infer_objects(copy=False)
        )

        # Convert numeric columns to appropriate types
        route_df['Lat'] = pd.to_numeric(route_df['Lat'], errors='coerce')
        route_df['Lon'] = pd.to_numeric(route_df['Lon'], errors='coerce')
        route_df['Elev'] = pd.to_numeric(route_df['Elev'], errors='coerce')
        route_df['MaxSpeed'] = pd.to_numeric(route_df['MaxSpeed'], errors='coerce')
        route_df['TrafficSpeed'] = pd.to_numeric(route_df['TrafficSpeed'], errors='coerce')
        route_df['BaseSpeed'] = pd.to_numeric(route_df['BaseSpeed'], errors='coerce')

        return route_df

    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """Geocode an address to coordinates.

        Args:
            address: Address string to geocode

        Returns:
            Coordinates (lat, lon) or None if not found
        """
        url = "https://geocode.search.hereapi.com/v1/geocode"

        params = {
            "apikey": self.api_key,
            "q": address
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if "items" in data and len(data["items"]) > 0:
                position = data["items"][0]["position"]
                return (position["lat"], position["lng"])

            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Geocoding request failed: {e}")
            return None

    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """Reverse geocode coordinates to address.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Address string or None if not found
        """
        url = "https://revgeocode.search.hereapi.com/v1/revgeocode"

        params = {
            "apikey": self.api_key,
            "at": f"{lat},{lon}"
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if "items" in data and len(data["items"]) > 0:
                return data["items"][0]["address"]["label"]

            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Reverse geocoding request failed: {e}")
            return None
