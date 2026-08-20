"""
Duty Cycle Predictor - API-style Interface

Example:
    # 使用默认参数
    predictor = DutyCyclePredictor()
    result = predictor.predict(
        origin=(52.292, 0.389),
        destination=(51.550, -0.242)
    )

    # 自定义参数
    result = predictor.predict(
        origin=(52.292, 0.389),
        destination=(51.550, -0.242),
        vehicle_params=VehicleParams(...),
        driving_behavior=DrivingBehavior(...)
    )
"""

import json
import logging
import os
import datetime
from math import radians, sin, cos, sqrt, asin
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
import pandas as pd

from dcpredictor.version import __version__, __version_info__, VERSION_DATE
from dcpredictor.utils.models import DutyCycle, VehicleParams, DrivingBehavior
from dcpredictor.utils.here_api import HereAPIClient
from dcpredictor.utils.srf_api import SRFAPIClient
from dcpredictor.generators.driving_cycle_generator import DrivingCycleGenerator
from dcpredictor.generators.elevation_gradient_generator import ElevationGradientGenerator
from dcpredictor.generators.energy_profile_generator import EnergyProfileGenerator

logger = logging.getLogger(__name__)


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两点间的 haversine 距离 (km)"""
    R = 6371.0  # 地球半径 (km)
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


def _is_route_df_valid(route_df: pd.DataFrame, min_distance_km: float = 5.0) -> bool:
    """
    检验 route_df 是否有效。

    检验条件：起点终点距离 >= min_distance_km

    Args:
        route_df: 路线 DataFrame
        min_distance_km: 最小距离阈值 (km)，默认 5km

    Returns:
        True 如果 route_df 有效，False 否则
    """
    if route_df is None or len(route_df) < 2:
        return False

    start_lat = route_df.iloc[0]["Lat"]
    start_lon = route_df.iloc[0]["Lon"]
    end_lat = route_df.iloc[-1]["Lat"]
    end_lon = route_df.iloc[-1]["Lon"]

    distance = _haversine_distance(start_lat, start_lon, end_lat, end_lon)

    if distance < min_distance_km:
        logger.warning(
            f"Route distance ({distance:.2f} km) is below threshold ({min_distance_km} km). "
            f"Start: ({start_lat:.5f}, {start_lon:.5f}), End: ({end_lat:.5f}, {end_lon:.5f})"
        )
        return False

    return True


# 默认参数 JSON 文件路径
_PARAMS_DIR = Path(__file__).parent / "params"
_VEHICLE_PARAMS_FILE = _PARAMS_DIR / "vehicle_params.json"
_DRIVING_BEHAVIOR_FILE = _PARAMS_DIR / "driving_behavior.json"


def load_default_vehicle_params(preset: str = "default") -> VehicleParams:
    """Load a vehicle-parameter preset from ``params/vehicle_params.json``.

    Args:
        preset: Preset key in the JSON file (e.g. ``"default"``, ``"AY71UCD"``,
            ``"FX73VAE"``).

    Returns:
        A populated :class:`VehicleParams` instance.

    Raises:
        KeyError: If ``preset`` is not present in the JSON file.
    """
    with open(_VEHICLE_PARAMS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if preset not in data:
        raise KeyError(f"Unknown vehicle preset '{preset}'. Available: {sorted(data)}")
    return VehicleParams.from_dict(data[preset])


def load_default_driving_behavior(preset: str = "default") -> DrivingBehavior:
    """Load a driving-behaviour preset from ``params/driving_behavior.json``.

    Args:
        preset: Preset key in the JSON file (currently only ``"default"``).

    Returns:
        A populated :class:`DrivingBehavior` instance.

    Raises:
        KeyError: If ``preset`` is not present in the JSON file.
    """
    with open(_DRIVING_BEHAVIOR_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if preset not in data:
        raise KeyError(
            f"Unknown driving-behaviour preset '{preset}'. Available: {sorted(data)}"
        )
    return DrivingBehavior.from_dict(data[preset])


# Backwards-compatible private aliases (kept for any internal/legacy callers).
_load_default_vehicle_params = load_default_vehicle_params
_load_default_driving_behavior = load_default_driving_behavior


class DutyCyclePredictor:
    """Duty Cycle 预测器"""

    def __init__(
        self,
        here_api_key: Optional[str] = None,
        srf_api_key: Optional[str] = None,
        env_file: Optional[str] = None,
    ):
        """
        初始化预测器。

        API keys 加载优先级:
        1. 手动提供的参数
        2. 环境变量 HERE_API_KEY / SRF_API_KEY
        3. .env 文件

        Args:
            here_api_key: HERE API key（可选）
            srf_api_key: SRF API key（可选）
            env_file: .env 文件路径（可选）
        """
        self._load_env_file(env_file)

        self._here_api_key = here_api_key or os.environ.get("HERE_API_KEY")
        self._srf_api_key = srf_api_key or os.environ.get("SRF_API_KEY")

        if not self._here_api_key:
            raise ValueError(
                "HERE API key is required. "
                "Set HERE_API_KEY in .env file or pass here_api_key parameter."
            )

        self._here_client = HereAPIClient(self._here_api_key)
        self._srf_client = SRFAPIClient(self._srf_api_key) if self._srf_api_key else None

        if not self._srf_api_key:
            logger.warning("SRF API key not provided. Elevation data will not be available.")

        self._driving_cycle_generator = DrivingCycleGenerator()
        self._elevation_gradient_generator = ElevationGradientGenerator()
        self._energy_profile_generator = EnergyProfileGenerator()

        logger.info("DutyCyclePredictor initialized")

    def _load_env_file(self, env_file: Optional[str] = None) -> None:
        """加载 .env 文件"""
        if env_file:
            env_path = Path(env_file)
        else:
            current = Path(__file__).resolve().parent
            env_path = None
            for _ in range(5):
                candidate = current / ".env"
                if candidate.exists():
                    env_path = candidate
                    break
                current = current.parent

        if env_path and env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded environment from {env_path}")

    def predict(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        mass_kg: float,
        vehicle_params: VehicleParams,
        driving_behavior: DrivingBehavior,
        departure_time: Optional[datetime.datetime] = None,
        via_points: Optional[List[Tuple[float, float]]] = None,
    ) -> Optional[DutyCycle]:
        """
        预测 Duty Cycle。

        Args:
            origin: 起点坐标 (lat, lon)
            destination: 终点坐标 (lat, lon)
            mass_kg: 车辆质量 (kg)
            vehicle_params: 车辆参数
            driving_behavior: 驾驶行为参数
            departure_time: 出发时间（可选）
            via_points: 途经点列表（可选）

        Returns:
            DutyCycle 预测结果，或 None（如果路线无效）
        """

        logger.info(f"Starting prediction: {origin} -> {destination}, mass={mass_kg}kg")

        # Step 1: 获取路线数据
        route_df = self._here_client.get_route_dataframe(
            origin, destination, via_points, departure_time
        )

        # Step 1.5: 检验 route_df 有效性
        if not _is_route_df_valid(route_df, min_distance_km=5.0):
            logger.warning("Skipping prediction due to invalid route_df")
            return None

        # # # # DEBUG ONLY:
        # route_df.to_csv("debug_route_data.csv", index=False)
        # print(route_df['Action'].value_counts())
        # print(route_df['MaxSpeed'].value_counts())  
        # print(route_df['BaseSpeed'].value_counts())
        # print(route_df['TrafficSpeed'].value_counts())

        # Step 2: 生成驾驶工况
        driving_cycle_df = self._driving_cycle_generator.generate_use_static_behaviour(
            route_df=route_df,
            departure_time=departure_time,
            v_cap=driving_behavior.v_cap,
            v_roundabout_enter=driving_behavior.v_roundabout_enter,
            v_turn=driving_behavior.v_turn,
            v_other_action=driving_behavior.v_other_action,
            a_acc=driving_behavior.a_acc,
            a_dec=driving_behavior.a_dec,
            v_cruise=driving_behavior.v_cruise,
            dt=driving_behavior.dt,
            smooth_speed=driving_behavior.smooth_speed,
        )

        # Step 3: 生成高程与坡度
        elevation_gradient_df = self._elevation_gradient_generator.generate_use_srf_api(
            driving_cycle_df=driving_cycle_df,
            srf_client=self._srf_client,
        )

        # Step 4: 计算能耗
        energy_profile_df = self._energy_profile_generator.generate_use_longitudinal_vehicle_dynamics(
            driving_cycle_df=driving_cycle_df,
            gradient_df=elevation_gradient_df,
            mass_kg=mass_kg,
            vehicle_params=vehicle_params,
        )

        return DutyCycle(
            speed_profile=driving_cycle_df,
            gradient_profile=elevation_gradient_df,
            energy_profile=energy_profile_df,
        )

    @property
    def version(self) -> str:
        return __version__

    @property
    def version_info(self) -> Dict[str, Any]:
        return {
            "version": __version__,
            "version_tuple": __version_info__,
            "release_date": VERSION_DATE,
        }
