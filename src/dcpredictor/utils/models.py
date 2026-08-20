"""
Data Models for Duty Cycle Prediction
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# =============================================================================
# Duty Cycle Result
# =============================================================================


@dataclass
class DutyCycle:
    """Container for duty cycle prediction results."""

    speed_profile: pd.DataFrame
    gradient_profile: pd.DataFrame
    energy_profile: pd.DataFrame

    # Reserved for future extensions
    weather_profile: Optional[pd.DataFrame] = None
    auxiliary_profile: Optional[pd.DataFrame] = None


# =============================================================================
# Vehicle Parameters
# =============================================================================


@dataclass
class VehicleParams:
    """
    车辆物理与动力系统参数（不含质量）

    Attributes:
        energy_type: 能源类型 ("diesel" 或 "electric")
        frontal_area_m2: 迎风面积 (m²)
        drag_coefficient: 风阻系数 (Cd)
        rolling_resistance_coeff: 滚动阻力系数 (Cr)
        transmission_efficiency: 传动效率（变速箱+传动轴）
        max_torque_nm: 最大扭矩 (Nm)

        # 柴油车专用参数
        engine_efficiency: 发动机热效率（柴油车）
        heating_value_mj_l: 燃料热值 (MJ/L)（柴油车）
        idle_fuel_consumption_l_per_hr: 怠速油耗 (L/hr)（柴油车）

        # 电动车专用参数
        battery_efficiency: 电池到电机能量转换效率（电动车）
    """

    # 通用参数
    energy_type: str  # "diesel" or "electric"
    frontal_area_m2: float
    drag_coefficient: float
    rolling_resistance_coeff: float
    transmission_efficiency: float
    max_torque_nm: float

    # 柴油车专用参数 (Optional for electric vehicles)
    engine_efficiency: Optional[float] = None
    heating_value_mj_l: Optional[float] = None
    idle_fuel_consumption_l_per_hr: Optional[float] = None

    # 电动车专用参数 (Optional for diesel vehicles)
    battery_efficiency: Optional[float] = None

    def is_electric(self) -> bool:
        """判断是否为电动车"""
        return self.energy_type.lower() == "electric"

    def is_diesel(self) -> bool:
        """判断是否为柴油车"""
        return self.energy_type.lower() == "diesel"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VehicleParams":
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


# =============================================================================
# Driving Behavior
# =============================================================================


@dataclass
class DrivingBehavior:
    """
    驾驶行为参数

    Attributes:
        v_cap: 最大车速 (m/s)
        v_cruise: 巡航速度 (m/s)
        a_acc: 默认加速度 (m/s²)
        a_dec: 默认减速度 (m/s²)
        v_roundabout_enter: 环岛入口限速 (m/s)
        v_turn: 转弯限速 (m/s)
        v_other_action: 其他动作限速 (m/s)
        dt: 仿真时间步长 (s)
        smooth_speed: 是否平滑速度曲线
    """

    v_cap: float
    v_cruise: float
    v_roundabout_enter: float
    v_turn: float
    v_other_action: float
    a_acc: float
    a_dec: float
    dt: float
    smooth_speed: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DrivingBehavior":
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


# =============================================================================
# Helper Functions
# =============================================================================


def _convert_for_json(obj: Any) -> Any:
    """Convert objects for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _convert_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_for_json(item) for item in obj]
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    return obj
