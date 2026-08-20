"""
Driving Cycle Generator Module

This module contains the DrivingCycleGenerator class for creating driving cycles
based on route data and vehicle parameters.
"""

import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from math import radians, sin, cos, asin, sqrt
from scipy.signal import savgol_filter
from typing import Optional


class DrivingCycleGenerator:
    """
    A class for generating driving cycles based on route data.

    This class creates realistic driving cycles that take into account
    vehicle dynamics, road conditions, and traffic constraints.
    """

    def __init__(self):
        """Initialize the driving cycle generator."""
        pass

    def generate_use_static_behaviour(
            self,
            route_df: pd.DataFrame,
            departure_time: datetime,
            v_cap: float = 25.0,                      # m/s, 25 m/s ≈ 90 km/h, 卡车最大车速
            v_roundabout_enter: float = 3.0,          # m/s, 环岛入口限速
            v_turn: float = 4.0,                     # m/s, 转弯限速
            v_other_action: float = 5.0,                 # m/s, 其他动作限速，后续可扩展
            a_acc: float = 0.58,                    # m/s², 默认加速度
            a_dec: float = 0.83,                    # m/s², 默认减速度
            dt: float = 1.0,                        # s, 仿真时间步长
            v_cruise: float = 25.0,                 # m/s, 巡航速度上限
            smooth_speed: bool = True               # 是否平滑速度曲线
        ) -> pd.DataFrame:
        """
        构造驾驶工况 (Driving Cycle)

        Args:
            route_df: DataFrame containing route information
            departure_time: Starting time for the driving cycle
            v_cap: Maximum vehicle speed (m/s)
            v_roundabout_enter: Speed limit at roundabout entrance (m/s)
            v_turn: Speed limit for turns (m/s)
            v_other_action: Speed limit for other actions (m/s)
            a_acc: Default acceleration (m/s²)
            a_dec: Default deceleration (m/s²)
            dt: Simulation time step (s)
            v_cruise: Cruise speed limit (m/s)
            smooth_speed: Whether to smooth the speed profile

        Returns:
            DataFrame containing the driving cycle with time, speed, and acceleration
        """
        # --- 基本检查 -------------------------------------------------------
        if len(route_df) < 2:
            raise ValueError("route_df 至少需要两行经纬度数据")

        # --- 预计算完整段长 seg_len ----------------------------------------
        lat = route_df['Lat'].values
        lon = route_df['Lon'].values
        lat_next = np.concatenate([lat[1:], lat[-1:]])
        lon_next = np.concatenate([lon[1:], lon[-1:]])
        route_df['seg_len'] = np.vectorize(self.haversine_distance)(lat, lon, lat_next, lon_next)
        route_df.iloc[-1, route_df.columns.get_loc('seg_len')] = 0.0 # 最后一个点段长为0

        # --- 初始化 DataFrame & 状态 ---------------------------------------
        dc_df = pd.DataFrame(columns=[
            'timestamp', 'Lat', 'Lon', 'distance', 'speed', 'speed_desired', 'acc', 'speed_traffic', 'speed_base', 'next_action', 'dist_to_next_action'
        ])

        t_cur = departure_time
        seg_idx_cur = 0
        lat_cur, lon_cur = route_df.at[0, 'Lat'], route_df.at[0, 'Lon']
        v_cur = 0.0
        v_desired = 0.0
        dist_total = 0.0

        # --- 主循环 ---------------------------------------------------------
        while seg_idx_cur < len(route_df) - 1:
            # 1. 本步应行驶距离
            dist_step = v_cur * dt
            dist_total += dist_step
            dist_remain = dist_step

            # 2. 跨段扣减 (使用剩余段长 remain_len 而非完整 seg_len)
            while seg_idx_cur < len(route_df) - 1:
                remain_len = self.haversine_distance(
                    lat_cur,
                    lon_cur,
                    route_df.at[seg_idx_cur + 1, 'Lat'],
                    route_df.at[seg_idx_cur + 1, 'Lon'],
                )
                if dist_remain <= remain_len:
                    break
                dist_remain -= remain_len
                seg_idx_cur += 1
                lat_cur, lon_cur = route_df.at[seg_idx_cur, 'Lat'], route_df.at[seg_idx_cur, 'Lon']

            # 3. 残余段内位移
            if dist_remain > 0 and seg_idx_cur < len(route_df) - 1:
                lat_cur, lon_cur = self._update_latlon(
                    route_df.at[seg_idx_cur, 'Lat'], route_df.at[seg_idx_cur, 'Lon'],
                    route_df.at[seg_idx_cur + 1, 'Lat'], route_df.at[seg_idx_cur + 1, 'Lon'],
                    lat_cur, lon_cur, dist_remain
                )

            # 4. 定义最大车速
            v_max = min(
                v_cap,
                route_df.at[seg_idx_cur, 'MaxSpeed'],
                route_df.at[seg_idx_cur, 'BaseSpeed'],
                route_df.at[seg_idx_cur, 'TrafficSpeed']
            )
            # print(v_max)

            # 5. 计算预瞄下一个动作的期望速度
            # 5.1 定义动作-速度映射
            action_speed_map = {
                'turn': v_turn,
                'uTurn': v_turn,
                'enterHighway': v_other_action,
                'exit': v_other_action,
                # 'ramp': v_other_action,
                'roundaboutEnter': v_roundabout_enter,
                'roundaboutPass': v_roundabout_enter,
                'arrive': 0.0,
            }

            # 5.2 搜索下一个动作，计算期望速度
            # 边界检查：如果内层循环已将 seg_idx_cur 推进到最后一段，跳出外层循环
            if seg_idx_cur >= len(route_df) - 1:
                break

            # 修复：初始值应为当前位置到当前段末端的剩余距离，而非0
            dist_cur_to_seg_end = self.haversine_distance(
                lat_cur, lon_cur,
                route_df.at[seg_idx_cur + 1, 'Lat'],
                route_df.at[seg_idx_cur + 1, 'Lon']
            )
            dist_2_next_action = dist_cur_to_seg_end
            next_action = None # 表示下一个动作类型

            seg_idx_tmp = seg_idx_cur + 1 # 从下一个seg index开始搜索
            while seg_idx_tmp < len(route_df):
                act = route_df.at[seg_idx_tmp, 'Action']
                if act in action_speed_map:
                    next_action = act
                    break
                dist_2_next_action += route_df.at[seg_idx_tmp, 'seg_len']
                seg_idx_tmp += 1

            if next_action is not None:
                v_desired = self.compute_desired_speed_2_next_action(
                    v_cur=v_cur,
                    v_target=action_speed_map[next_action],
                    v_cruise=v_cruise,
                    dist_2_next_action=dist_2_next_action,
                    a_acc=a_acc,
                    a_dec=a_dec
                )
            else:
                v_desired = v_max
        
            # 6. 更新最终期望速度 & 当前速度
            v_desired = min(v_desired, v_max)
            v_cur = self._update_speed(v_cur, v_desired, a_acc, a_dec, dt)

            # 7. 记录数据
            dc_df.loc[len(dc_df)] = {
                'timestamp': t_cur,
                'Lat': lat_cur,
                'Lon': lon_cur,
                'distance': dist_total,
                'speed': v_cur,
                'speed_desired': v_desired,
                'speed_traffic': route_df.at[seg_idx_cur, 'TrafficSpeed'],
                'speed_base': route_df.at[seg_idx_cur, 'BaseSpeed'],
                'next_action': next_action,
                'dist_to_next_action': dist_2_next_action
            }

            # 8. 时间推进
            t_cur += timedelta(seconds=dt)

            # 9. 到达终点判断 (defensive: verify we're actually near the end)
            if next_action == 'arrive' and v_cur <= 1e-3:
                remaining_segments = len(route_df) - seg_idx_cur - 1
                if remaining_segments <= 3:  # Allow termination within last 3 segments
                    print("Arrived at destination.")
                    break
                else:
                    # Erroneous intermediate 'arrive' action, continue driving
                    next_action = None

            # 10. 进度输出
            if len(dc_df) % 1000 == 0:
                print(
                    f"Step {len(dc_df)} | t: {t_cur} | seg: {seg_idx_cur} | "
                    f"gps: ({lat_cur:.6f},{lon_cur:.6f}) | v/v_desired: {v_cur:.2f}/{v_desired:.2f} m/s | "
                    f"dist: {dist_total/1000:.2f} km | next_action: {next_action}"
                )

        # --- 最终减速停车 -----------------------------------------------------
        # 如果主循环结束时车辆仍在移动，继续减速直到停止
        final_lat = route_df.at[len(route_df) - 1, 'Lat']
        final_lon = route_df.at[len(route_df) - 1, 'Lon']

        while v_cur > 1e-3:
            # 减速
            v_cur = max(v_cur - a_dec * dt, 0.0)

            # 计算本步行驶距离
            dist_step = v_cur * dt
            dist_total += dist_step

            # 更新位置（向终点插值）
            dist_to_final = self.haversine_distance(lat_cur, lon_cur, final_lat, final_lon)
            if dist_to_final > 0 and dist_step > 0:
                ratio = min(dist_step / dist_to_final, 1.0)
                lat_cur = lat_cur + (final_lat - lat_cur) * ratio
                lon_cur = lon_cur + (final_lon - lon_cur) * ratio

            # 记录数据
            dc_df.loc[len(dc_df)] = {
                'timestamp': t_cur,
                'Lat': lat_cur,
                'Lon': lon_cur,
                'distance': dist_total,
                'speed': v_cur,
                'speed_desired': 0.0,
                'speed_traffic': route_df.at[len(route_df) - 1, 'TrafficSpeed'],
                'speed_base': route_df.at[len(route_df) - 1, 'BaseSpeed'],
                'next_action': 'arrive',
                'dist_to_next_action': max(0, dist_to_final - dist_step)
            }

            t_cur += timedelta(seconds=dt)

        # 最后一个点：速度为0，位置为终点
        dc_df.loc[len(dc_df)] = {
            'timestamp': t_cur,
            'Lat': final_lat,
            'Lon': final_lon,
            'distance': dist_total,
            'speed': 0.0,
            'speed_desired': 0.0,
            'speed_traffic': route_df.at[len(route_df) - 1, 'TrafficSpeed'],
            'speed_base': route_df.at[len(route_df) - 1, 'BaseSpeed'],
            'next_action': 'arrive',
            'dist_to_next_action': 0.0
        }
        print("Arrived at destination.")

        # --- 后处理 ---------------------------------------------------------
        if smooth_speed and len(dc_df) >= 5:
            win = min(len(dc_df) // 2 * 2 + 1, 11)
            dc_df['speed'] = savgol_filter(dc_df['speed'], window_length=win, polyorder=3, mode='nearest')
            # 再次用v_max限幅
            dc_df['speed'] = dc_df['speed'].clip(upper=v_cap)

        dc_df['acc'] = dc_df['speed'].diff().fillna(0.0) / dt
        dc_df['timestamp'] = pd.to_datetime(dc_df['timestamp'], errors='coerce')

        return dc_df

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        计算两个GPS坐标之间的距离（米）
        """
        R = 6371000  # 地球半径，单位米
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        return 2 * R * asin(sqrt(a))

    @staticmethod
    def compute_desired_speed_2_next_action(
        v_cur: float,
        v_target: float,
        v_cruise: float,
        dist_2_next_action: float,
        a_acc: float,
        a_dec: float
    ) -> float:
        """
        计算到达下一个动作点时应保持的期望速度。

        核心思路：
        - 计算在给定距离内能减速到 v_target 的最大安全速度 (v_safe_max)
        - 期望速度 = min(v_cruise, v_safe_max)
        - 这样既能尽量保持巡航速度，又能保证及时减速

        """
        # 运动学公式: v² = v_target² + 2 * a_dec * dist
        # v_safe_max 是当前能拥有的最大速度，使得在 dist 距离内能减速到 v_target
        v_safe_max = sqrt(v_target**2 + 2 * a_dec * dist_2_next_action)

        # 期望速度：以巡航速度为目标，但不超过安全上限
        v_desired = min(v_cruise, v_safe_max)

        return v_desired

    @staticmethod
    def interpolate_speed(v_start: float, v_end: float, ratio: float) -> float:
        """线性插值计算中间速度"""
        return v_start + ratio * (v_end - v_start)

    @staticmethod
    def _update_speed(v_cur: float, v_desired: float, a_acc: float, a_dec: float, dt: float) -> float:
        """更新当前速度"""
        if v_desired > v_cur:
            v_new = min(v_cur + a_acc * dt, v_desired)
        else:
            v_new = max(v_cur - a_dec * dt, v_desired)
        return v_new

    @staticmethod
    def _update_latlon(lat1: float, lon1: float, lat2: float, lon2: float,
                      lat_cur: float, lon_cur: float, dist: float) -> tuple:
        """根据当前路段起点终点的经纬度和已行驶距离占比，等比例插值计算当前位置"""
        total_dist = DrivingCycleGenerator.haversine_distance(lat1, lon1, lat2, lon2)
        if total_dist == 0:
            return lat1, lon1
        ratio = dist / total_dist
        lat = lat_cur + (lat2 - lat1) * ratio
        lon = lon_cur + (lon2 - lon1) * ratio
        return lat, lon
