"""
Energy Profile Generator Module

根据驾驶工况和坡度数据计算能耗曲线。
"""

import pandas as pd
import numpy as np
from typing import Optional
import logging

from dcpredictor.params import VehicleParams

logger = logging.getLogger(__name__)


class EnergyProfileGenerator:
    """
    能耗曲线生成器

    根据驾驶工况和坡度数据，基于纵向车辆动力学模型计算功率和油耗。
    """

    def __init__(self):
        """初始化生成器"""
        pass

    def _calculate_wheel_power(
        self,
        mass_kg: float,
        gradient_degrees: float,
        velocity_mps: float,
        acceleration_mps2: float,
        rolling_resistance_coeff: float = 0.00464,
        drag_coefficient: float = 0.5,
        frontal_area_m2: float = 10.0,
        air_density_kg_m3: float = 1.225,
        g: float = 9.81
    ) -> float:
        """
        基于车辆动力学计算瞬时轮端功率。

        计算克服四种主要阻力所需的总牵引力:
        - 滚动阻力
        - 坡度阻力
        - 空气阻力
        - 加速阻力

        Args:
            mass_kg: 车辆总质量 (kg)
            gradient_degrees: 道路坡度 (度)。正值为上坡，负值为下坡
            velocity_mps: 瞬时车速 (m/s)
            acceleration_mps2: 瞬时加速度 (m/s²)
            rolling_resistance_coeff: 滚动阻力系数，默认 0.00464
            drag_coefficient: 空气阻力系数，默认 0.5
            frontal_area_m2: 车辆迎风面积 (m²)，默认 10.0
            air_density_kg_m3: 空气密度 (kg/m³)，默认 1.225
            g: 重力加速度 (m/s²)，默认 9.81

        Returns:
            轮端功率 (W)
        """
        # 将坡度从度转换为弧度
        gradient_radians = np.radians(gradient_degrees)

        # 计算各分力
        # 1. 滚动阻力
        F_roll = rolling_resistance_coeff * mass_kg * g * np.cos(gradient_radians)

        # 2. 坡度阻力
        F_grade = mass_kg * g * np.sin(gradient_radians)

        # 3. 空气阻力
        F_aero = 0.5 * air_density_kg_m3 * drag_coefficient * frontal_area_m2 * velocity_mps**2

        # 4. 加速阻力
        F_accel = mass_kg * acceleration_mps2

        # 总牵引力
        F_total = F_roll + F_grade + F_aero + F_accel

        # 计算轮端功率 (力 × 速度)
        power_watts = F_total * velocity_mps

        return power_watts

    def _calculate_diesel_consumption_rate(
        self,
        wheel_power_watts: float,
        heating_value_mj_l: float = 36.0,
        engine_efficiency: float = 0.42,
        transmission_efficiency: float = 0.95,
        idle_fuel_consumption_l_per_hr: float = 0.0
    ) -> float:
        """
        基于轮端功率计算瞬时柴油消耗率。

        Args:
            wheel_power_watts: 瞬时轮端功率 (W)
            heating_value_mj_l: 柴油低热值 (MJ/L)，默认 36.0
            engine_efficiency: 发动机热效率，默认 0.42 (42%)
            transmission_efficiency: 传动系统效率 (发动机到车轮)，默认 0.95
            idle_fuel_consumption_l_per_hr: 怠速油耗 (L/hr)，默认 0.0

        Returns:
            油耗率 (L/hr)
        """
        # 负功率（制动/滑行）时，按怠速油耗计算
        if wheel_power_watts <= 0:
            return idle_fuel_consumption_l_per_hr

        # 1. 从轮端功率计算发动机功率
        engine_power_watts = wheel_power_watts / transmission_efficiency

        # 2. 从发动机功率计算所需燃料功率
        fuel_power_watts = engine_power_watts / engine_efficiency

        # 3. 将热值从 MJ/L 转换为 J/L
        heating_value_j_l = heating_value_mj_l * 1e6

        # 4. 计算油耗率 (L/s)
        fuel_rate_l_s = fuel_power_watts / heating_value_j_l

        # 5. 转换为 L/hr
        fuel_rate_l_hr = fuel_rate_l_s * 3600

        return fuel_rate_l_hr

    def _calculate_electric_consumption_rate(
        self,
        wheel_power_watts: float,
        battery_efficiency: float = 0.90,
        transmission_efficiency: float = 0.95,
        regeneration_efficiency: Optional[float] = None
    ) -> float:
        """
        基于轮端功率计算瞬时电力消耗率。

        Args:
            wheel_power_watts: 瞬时轮端功率 (W)
            battery_efficiency: 电池到电机能量转换效率，默认 0.90 (90%)
            transmission_efficiency: 传动系统效率 (电机到车轮)，默认 0.95
            regeneration_efficiency: 制动能量回收效率，默认 None, 表示不考虑回收
        Returns:
            电力消耗率 (kW)，正值为耗电，负值为回收（制动能量回收）
        """
        # 电动车支持制动能量回收，所以负功率也可以计算
        # 假设回收效率为 battery_efficiency * transmission_efficiency

        if wheel_power_watts <= 0:
            # 制动能量回收：轮端负功率 -> 电池充电
            if regeneration_efficiency is None:
                battery_power_watts = 0
            else:
                battery_power_watts = wheel_power_watts * regeneration_efficiency
        else:
            # 驱动：电池 -> 电机 -> 车轮
            # 电池功率 = 轮端功率 / (传动效率 * 电池放电效率)
            battery_power_watts = wheel_power_watts / (transmission_efficiency * battery_efficiency)

        # 返回电池功率 (kW)
        return battery_power_watts / 1000.0

    def generate_use_longitudinal_vehicle_dynamics(
        self,
        driving_cycle_df: pd.DataFrame,
        gradient_df: pd.DataFrame,
        mass_kg: float,
        vehicle_params: VehicleParams,
        dt: float = 1.0
    ) -> pd.DataFrame:
        """
        使用纵向车辆动力学模型计算能耗曲线

        Args:
            driving_cycle_df: 驾驶工况DataFrame，包含 timestamp, speed, acc 列
            gradient_df: 坡度DataFrame，包含 gradient 列
            mass_kg: 车辆质量 (kg)
            vehicle_params: 车辆参数
            dt: 时间步长（秒）

        Returns:
            对于柴油车: DataFrame，包含 timestamp, distance, speed, acc, gradient,
                        wheel_power_kW, engine_power_kW, fuel_rate_L_hr, fuel_cumulative_L 列
            对于电动车: DataFrame，包含 timestamp, distance, speed, acc, gradient,
                        wheel_power_kW, engine_power_kW, energy_rate_kW, energy_cumulative_kWh 列
        """
        # 复制基础数据
        energy_df = driving_cycle_df[["timestamp", "distance", "speed", "acc"]].copy()

        # 对齐坡度数据（插值到相同长度）
        gradients = self._interpolate_gradients(gradient_df, len(driving_cycle_df))
        energy_df["gradient"] = gradients

        # 判断车辆类型
        is_electric = vehicle_params.is_electric()

        # 计算功率和能耗
        power_kw = []
        energy_rate = []  # L/hr for diesel, kW for electric

        for _, row in energy_df.iterrows():
            velocity = row["speed"]
            acceleration = row["acc"] if not pd.isna(row["acc"]) else 0.0
            gradient = row["gradient"]

            # 计算轮端功率
            power_w = self._calculate_wheel_power(
                mass_kg=mass_kg,
                gradient_degrees=gradient,
                velocity_mps=velocity,
                acceleration_mps2=acceleration,
                rolling_resistance_coeff=vehicle_params.rolling_resistance_coeff,
                drag_coefficient=vehicle_params.drag_coefficient,
                frontal_area_m2=vehicle_params.frontal_area_m2,
            )
            power_kw.append(power_w / 1000.0)

            if is_electric:
                # 电动车：计算电力消耗
                rate = self._calculate_electric_consumption_rate(
                    wheel_power_watts=power_w,
                    battery_efficiency=vehicle_params.battery_efficiency or 0.90,
                    transmission_efficiency=vehicle_params.transmission_efficiency,
                    regeneration_efficiency=None, # TODO: 可选添加回收效率参数,暂时未开发
                )
                energy_rate.append(rate)
            else:
                # 柴油车：计算油耗
                rate = self._calculate_diesel_consumption_rate(
                    wheel_power_watts=power_w,
                    heating_value_mj_l=vehicle_params.heating_value_mj_l or 36.0,
                    engine_efficiency=vehicle_params.engine_efficiency or 0.42,
                    transmission_efficiency=vehicle_params.transmission_efficiency,
                    idle_fuel_consumption_l_per_hr=vehicle_params.idle_fuel_consumption_l_per_hr or 0.0,
                )
                energy_rate.append(rate)

        energy_df["wheel_power_kW"] = power_kw
        energy_df["engine_power_kW"] = energy_df["wheel_power_kW"] / vehicle_params.transmission_efficiency

        if is_electric:
            # 电动车输出
            energy_df["energy_rate_kW"] = energy_rate
            # 计算累计电耗 (kWh): kW * dt(hr) = kWh
            dt_hr = dt / 3600.0
            energy_df["energy_cumulative_kWh"] = (energy_df["energy_rate_kW"] * dt_hr).cumsum()
            logger.info(f"Energy profile (electric) calculated: {len(energy_df)} points")
        else:
            # 柴油车输出
            energy_df["fuel_rate_L_hr"] = energy_rate
            # 计算累计油耗 (L): L/hr * dt(hr) = L
            dt_hr = dt / 3600.0
            energy_df["fuel_cumulative_L"] = (energy_df["fuel_rate_L_hr"] * dt_hr).cumsum()
            logger.info(f"Energy profile (diesel) calculated: {len(energy_df)} points")

        return energy_df

    def _interpolate_gradients(
        self,
        gradient_df: pd.DataFrame,
        target_length: int
    ) -> list:
        """
        将坡度数据插值到目标长度

        Args:
            gradient_df: 坡度DataFrame，包含 gradient 列
            target_length: 目标长度

        Returns:
            插值后的坡度列表
        """
        if len(gradient_df) == 0:
            return [0.0] * target_length

        if "gradient" not in gradient_df.columns:
            return [0.0] * target_length

        gradients = gradient_df["gradient"].values

        if len(gradients) == target_length:
            return gradients.tolist()

        # 线性插值
        old_indices = np.linspace(0, len(gradients) - 1, len(gradients))
        new_indices = np.linspace(0, len(gradients) - 1, target_length)
        interpolated = np.interp(new_indices, old_indices, gradients)

        return interpolated.tolist()

    def compute_summary(
        self,
        driving_cycle_df: pd.DataFrame,
        gradient_df: pd.DataFrame,
        energy_df: pd.DataFrame,
        mass_kg: float,
        vehicle_params: VehicleParams
    ) -> dict:
        """
        计算汇总统计信息

        Args:
            driving_cycle_df: 驾驶工况DataFrame
            gradient_df: 坡度DataFrame
            energy_df: 能耗DataFrame
            mass_kg: 车辆质量 (kg)
            vehicle_params: 车辆参数

        Returns:
            汇总统计字典
        """
        is_electric = vehicle_params.is_electric()

        summary = {
            "energy_type": vehicle_params.energy_type,
            "total_distance_km": driving_cycle_df["distance"].max() / 1000.0,
            "duration_min": len(driving_cycle_df) / 60.0,
            "avg_speed_kmh": driving_cycle_df["speed"].mean() * 3.6,
            "max_speed_kmh": driving_cycle_df["speed"].max() * 3.6,
            "min_speed_kmh": driving_cycle_df["speed"].min() * 3.6,
            "max_wheel_power_kW": energy_df["wheel_power_kW"].max(),
            "avg_wheel_power_kW": energy_df["wheel_power_kW"].mean(),
            "max_engine_power_kW": energy_df["engine_power_kW"].max(),
            "avg_engine_power_kW": energy_df["engine_power_kW"].mean(),
            "vehicle_mass_kg": mass_kg,
        }

        if is_electric:
            # 电动车能耗统计
            summary["total_energy_kWh"] = energy_df["energy_cumulative_kWh"].iloc[-1]
            summary["avg_energy_rate_kW"] = energy_df["energy_rate_kW"].mean()

            # 电耗经济性 (kWh/100km)
            if summary["total_distance_km"] > 0:
                summary["energy_economy_kWh_per_100km"] = (
                    summary["total_energy_kWh"] / summary["total_distance_km"] * 100
                )
            else:
                summary["energy_economy_kWh_per_100km"] = 0.0
        else:
            # 柴油车油耗统计
            summary["total_fuel_L"] = energy_df["fuel_cumulative_L"].iloc[-1]
            summary["avg_fuel_rate_L_hr"] = energy_df["fuel_rate_L_hr"].mean()

            # 油耗经济性 (L/100km)
            if summary["total_distance_km"] > 0:
                summary["fuel_economy_L_per_100km"] = (
                    summary["total_fuel_L"] / summary["total_distance_km"] * 100
                )
            else:
                summary["fuel_economy_L_per_100km"] = 0.0

        # 坡度统计
        if "gradient" in gradient_df.columns:
            summary["max_gradient_deg"] = gradient_df["gradient"].max()
            summary["min_gradient_deg"] = gradient_df["gradient"].min()
            summary["avg_gradient_deg"] = gradient_df["gradient"].mean()

        # 高程统计
        if "cumulative_elevation_gain" in gradient_df.columns:
            summary["total_elevation_gain_m"] = gradient_df["cumulative_elevation_gain"].max()
        if "cumulative_elevation_loss" in gradient_df.columns:
            summary["total_elevation_loss_m"] = gradient_df["cumulative_elevation_loss"].max()

        return summary
