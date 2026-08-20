"""
Elevation Gradient Generator Module

根据驾驶工况数据中的经纬度，获取高程数据并计算坡度。
"""

import pandas as pd
import numpy as np
from typing import Optional
from math import radians, sin, cos, asin, sqrt
import logging

logger = logging.getLogger(__name__)


class ElevationGradientGenerator:
    """
    高程与坡度生成器

    根据经纬度坐标获取高程数据，并计算路段坡度。
    """

    def __init__(self):
        """初始化生成器"""
        pass

    def generate_use_srf_api(
        self,
        driving_cycle_df: pd.DataFrame,
        srf_client,
        lat_col: str = "Lat",
        lon_col: str = "Lon",
        smoothing_window: int = 5,
        max_gradient_degrees: float = 8.0
    ) -> pd.DataFrame:
        """
        使用SRF API获取高程数据并生成坡度曲线

        Args:
            driving_cycle_df: 包含经纬度的DataFrame，包含Lat, Lon列
            srf_client: SRFAPIClient实例
            lat_col: 纬度列名
            lon_col: 经度列名
            smoothing_window: 坡度平滑窗口大小
            max_gradient_degrees: 最大坡度限制（度）

        Returns:
            DataFrame，包含 elevation, gradient 列
        """
        if srf_client is None:
            logger.warning("SRF client is None, using zero elevation")
            return self._generate_zero_elevation(driving_cycle_df, lat_col, lon_col)

        # 提取坐标
        coordinates = [
            (row[lat_col], row[lon_col])
            for _, row in driving_cycle_df.iterrows()
        ]

        # 获取高程数据
        try:
            elevations = srf_client.get_elevation_batch(coordinates)
            logger.info(f"Elevation data obtained for {len(elevations)} points")
        except Exception as e:
            logger.warning(f"Failed to get elevation from SRF API: {e}")
            return self._generate_zero_elevation(driving_cycle_df, lat_col, lon_col)
        
        # 构建结果DataFrame
        result_df = pd.DataFrame({
            lat_col: driving_cycle_df[lat_col].values,
            lon_col: driving_cycle_df[lon_col].values,
            "elevation": elevations
        })

        
        # 计算段距离
        result_df = self._calculate_segment_distances(result_df, lat_col, lon_col)

        # 计算原始坡度
        result_df = self._calculate_raw_gradients(result_df)

        # 平滑坡度
        result_df = self._smooth_gradients(result_df, smoothing_window)

        # 限制坡度范围,当超过最大坡度时则截断为最大坡度
        result_df = self._limit_gradients(result_df, max_gradient_degrees)

        # 计算累计高程变化
        result_df = self._calculate_cumulative_elevation_changes(result_df)

        return result_df

    def _generate_zero_elevation(
        self,
        driving_cycle_df: pd.DataFrame,
        lat_col: str,
        lon_col: str
    ) -> pd.DataFrame:
        """生成零高程数据（当API不可用时）"""
        n = len(driving_cycle_df)
        result_df = pd.DataFrame({
            lat_col: driving_cycle_df[lat_col].values,
            lon_col: driving_cycle_df[lon_col].values,
            "elevation": [0.0] * n,
            "segment_distance": [0.0] * n,
            "cumulative_distance": np.cumsum([0.0] * n),
            "raw_gradient": [0.0] * n,
            "gradient": [0.0] * n,
            "cumulative_elevation_gain": [0.0] * n,
            "cumulative_elevation_loss": [0.0] * n,
        })
        return result_df

    def _calculate_segment_distances(
        self,
        df: pd.DataFrame,
        lat_col: str,
        lon_col: str
    ) -> pd.DataFrame:
        """计算相邻点之间的距离"""
        df = df.copy()
        distances = [0.0]

        for i in range(1, len(df)):
            dist = self._haversine_distance(
                df.iloc[i-1][lat_col], df.iloc[i-1][lon_col],
                df.iloc[i][lat_col], df.iloc[i][lon_col]
            )
            distances.append(dist)

        df["segment_distance"] = distances
        df["cumulative_distance"] = np.cumsum(distances)

        return df

    def _calculate_raw_gradients(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算原始坡度"""
        df = df.copy()
        gradients = [0.0]

        for i in range(1, len(df)):
            elevation_change = df.iloc[i]["elevation"] - df.iloc[i-1]["elevation"]
            distance = df.iloc[i]["segment_distance"]

            if distance > 0 and not (np.isnan(elevation_change) or np.isnan(distance)):
                gradient_rad = np.arctan(elevation_change / distance)
                gradient_deg = np.degrees(gradient_rad)
                gradients.append(gradient_deg)
            else:
                gradients.append(0.0)

        df["raw_gradient"] = gradients
        return df

    def _smooth_gradients(self, df: pd.DataFrame, window_size: int) -> pd.DataFrame:
        """平滑坡度数据"""
        df = df.copy()

        if len(df) < window_size:
            df["gradient"] = df["raw_gradient"]
            return df

        df["gradient"] = df["raw_gradient"].rolling(
            window=window_size,
            center=True,
            min_periods=1
        ).mean()

        return df

    def _limit_gradients(self, df: pd.DataFrame, max_gradient_degrees: float) -> pd.DataFrame:
        """限制坡度范围"""
        df = df.copy()
        df["gradient"] = np.clip(
            df["gradient"],
            -max_gradient_degrees,
            max_gradient_degrees
        )
        return df

    def _calculate_cumulative_elevation_changes(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算累计爬升和下降"""
        df = df.copy()

        elevation_gain = 0.0
        elevation_loss = 0.0
        gains = [0.0]
        losses = [0.0]

        for i in range(1, len(df)):
            distance = df.iloc[i]["segment_distance"]
            gradient_rad = np.radians(df.iloc[i]["gradient"])
            elevation_change = distance * np.sin(gradient_rad)

            if elevation_change > 0:
                elevation_gain += elevation_change
            else:
                elevation_loss += abs(elevation_change)

            gains.append(elevation_gain)
            losses.append(elevation_loss)

        df["cumulative_elevation_gain"] = gains
        df["cumulative_elevation_loss"] = losses

        return df

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两个GPS坐标之间的距离（米）"""
        R = 6371000
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        return 2 * R * asin(sqrt(a))
