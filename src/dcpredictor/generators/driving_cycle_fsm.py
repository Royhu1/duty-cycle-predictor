"""
Driving Cycle Generator using Finite State Machine

状态机驾驶工况生成器，基于原始 DrivingCycleGenerator 逻辑实现，
保持接口兼容性以便进行对比测试。

核心改进：
1. 使用状态机架构，逻辑更清晰
2. 修复 dist_2_next_action 计算（使用当前位置到段末的距离）
3. 修复 _update_latlon 插值错误（从段起点开始插值）
4. 添加 'depart' 动作处理
5. 处理 v_max 为 NaN 的情况
"""

from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from math import radians, sin, cos, asin, sqrt

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter


class VehicleState(Enum):
    """车辆状态枚举"""
    STOPPED = auto()       # 停止（起点或完成动作后短暂停止）
    ACCELERATING = auto()  # 加速中
    CRUISING = auto()      # 巡航（匀速）
    DECELERATING = auto()  # 减速中（接近动作点）
    ARRIVED = auto()       # 到达终点


@dataclass
class DrivingParams:
    """驾驶参数"""
    v_cap: float = 25.0           # m/s, 最大车速
    v_cruise: float = 25.0        # m/s, 巡航速度
    v_turn: float = 4.0           # m/s, 转弯限速
    v_roundabout: float = 3.0     # m/s, 环岛限速
    v_other_action: float = 5.0   # m/s, 其他动作限速
    a_acc: float = 0.58           # m/s², 加速度
    a_dec: float = 0.83           # m/s², 减速度
    dt: float = 1.0               # s, 时间步长
    smooth_speed: bool = True     # 是否平滑速度曲线


@dataclass
class VehicleContext:
    """车辆上下文"""
    # 位置状态
    lat: float = 0.0
    lon: float = 0.0
    seg_idx: int = 0
    dist_in_seg: float = 0.0      # 当前段内已行驶距离
    dist_total: float = 0.0       # 总行驶距离

    # 速度状态
    speed: float = 0.0
    speed_desired: float = 0.0    # 期望速度（与原版一致）

    # 感知信息（每步更新）
    v_max: float = 25.0           # 当前路段最大允许速度
    v_target: float = 0.0         # 下一个动作的目标速度
    dist_to_action: float = 0.0   # 到下一个动作的距离
    next_action: Optional[str] = None
    next_action_seg_idx: int = -1

    # 调试信息
    speed_traffic: float = 0.0
    speed_base: float = 0.0


class DrivingCycleFSM:
    """状态机驾驶工况生成器"""

    # 动作-速度映射（类常量）
    ACTION_SPEED_MAP = {
        'turn': 'v_turn',
        'uTurn': 'v_turn',
        'enterHighway': 'v_other_action',
        'exit': 'v_other_action',
        'ramp': 'v_other_action',
        'roundaboutEnter': 'v_roundabout',
        'roundaboutPass': 'v_roundabout',
        'arrive': 0.0,
    }

    def __init__(self, route_df: pd.DataFrame, params: Optional[DrivingParams] = None):
        """
        初始化状态机驾驶工况生成器

        Args:
            route_df: 路线数据，包含 Lat, Lon, Action, MaxSpeed, BaseSpeed, TrafficSpeed 等列
            params: 驾驶参数，如果为 None 则使用默认值
        """
        self.route_df = route_df.copy()
        self.params = params or DrivingParams()
        self.state = VehicleState.STOPPED
        self.context = VehicleContext()

        # 预计算段长
        self._precompute_seg_lengths()

        # 初始化位置
        self.context.lat = self.route_df.at[0, 'Lat']
        self.context.lon = self.route_df.at[0, 'Lon']

    def _precompute_seg_lengths(self):
        """预计算每段长度"""
        lats = self.route_df['Lat'].values
        lons = self.route_df['Lon'].values

        seg_lens = []
        for i in range(len(lats) - 1):
            seg_lens.append(self._haversine(lats[i], lons[i], lats[i+1], lons[i+1]))
        seg_lens.append(0.0)  # 最后一点段长为 0

        self.route_df['seg_len'] = seg_lens

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        计算两点间距离（米）

        使用 Haversine 公式计算地球表面两点间的大圆距离
        """
        R = 6371000  # 地球半径，单位米
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        return 2 * R * asin(sqrt(a))

    def _get_action_target_speed(self, action: str) -> float:
        """获取动作对应的目标速度"""
        if action not in self.ACTION_SPEED_MAP:
            return self.params.v_cruise

        val = self.ACTION_SPEED_MAP[action]
        if isinstance(val, str):
            return getattr(self.params, val)
        return val

    # =========================================================================
    # 感知更新
    # =========================================================================

    def _update_perception(self):
        """更新感知信息：v_max, 下一个动作, 距离等"""
        ctx = self.context
        df = self.route_df
        seg = ctx.seg_idx
        p = self.params

        # 1. 更新当前路段最大速度（取最小值，忽略 NaN 和无穷大）
        speed_candidates = [p.v_cap, p.v_cruise]

        # 安全获取速度值，忽略 NaN
        for col in ['MaxSpeed', 'BaseSpeed', 'TrafficSpeed']:
            if col in df.columns:
                val = df.at[seg, col]
                if pd.notna(val) and np.isfinite(val) and val > 0:
                    speed_candidates.append(val)

        ctx.v_max = min(speed_candidates)

        # 保存调试信息
        if 'TrafficSpeed' in df.columns:
            ctx.speed_traffic = df.at[seg, 'TrafficSpeed'] if pd.notna(df.at[seg, 'TrafficSpeed']) else 0.0
        if 'BaseSpeed' in df.columns:
            ctx.speed_base = df.at[seg, 'BaseSpeed'] if pd.notna(df.at[seg, 'BaseSpeed']) else 0.0

        # 2. 搜索下一个动作
        ctx.next_action = None
        ctx.next_action_seg_idx = -1

        # 当前段剩余距离（关键：用当前位置到段末的距离，而非整段长度）
        seg_len = df.at[seg, 'seg_len']
        ctx.dist_to_action = seg_len - ctx.dist_in_seg

        # 从下一段开始搜索
        for i in range(seg + 1, len(df)):
            action = df.at[i, 'Action'] if 'Action' in df.columns else None
            if action in self.ACTION_SPEED_MAP:
                ctx.next_action = action
                ctx.next_action_seg_idx = i
                ctx.v_target = self._get_action_target_speed(action)
                break
            ctx.dist_to_action += df.at[i, 'seg_len']

        # 如果没找到动作，设为巡航
        if ctx.next_action is None:
            ctx.v_target = ctx.v_max
            ctx.dist_to_action = float('inf')

    def _compute_desired_speed(self) -> float:
        """
        计算期望速度（与原版 compute_desired_speed_2_next_action 逻辑一致）

        核心思路：
        - 计算在给定距离内能减速到 v_target 的最大安全速度 (v_safe_max)
        - 期望速度 = min(v_cruise, v_safe_max)
        - 最终期望速度 = min(期望速度, v_max)
        """
        ctx = self.context
        p = self.params

        if ctx.next_action is None:
            return ctx.v_max

        # 运动学公式: v² = v_target² + 2 * a_dec * dist
        # v_safe_max 是当前能拥有的最大速度，使得在 dist 距离内能减速到 v_target
        v_safe_max = sqrt(ctx.v_target**2 + 2 * p.a_dec * ctx.dist_to_action)

        # 期望速度：以巡航速度为目标，但不超过安全上限
        v_desired = min(p.v_cruise, v_safe_max)

        # 不超过路段限速
        v_desired = min(v_desired, ctx.v_max)

        return v_desired

    # =========================================================================
    # 速度更新（与原版 _update_speed 逻辑一致）
    # =========================================================================

    def _update_speed(self):
        """更新当前速度（与原版逻辑一致）"""
        ctx = self.context
        p = self.params

        v_desired = ctx.speed_desired

        if v_desired > ctx.speed:
            ctx.speed = min(ctx.speed + p.a_acc * p.dt, v_desired)
        else:
            ctx.speed = max(ctx.speed - p.a_dec * p.dt, v_desired)

    # =========================================================================
    # 状态转移
    # =========================================================================

    def _check_transitions(self):
        """检查并执行状态转移"""
        ctx = self.context
        p = self.params

        # 计算制动距离
        braking_dist = (ctx.speed**2 - ctx.v_target**2) / (2 * p.a_dec) if ctx.speed > ctx.v_target else 0
        need_brake = ctx.dist_to_action <= braking_dist

        if self.state == VehicleState.STOPPED:
            # 关键：STOPPED 状态下，只要不是已到达终点，就开始加速
            if ctx.next_action == 'arrive' and ctx.dist_to_action < 10:
                self.state = VehicleState.ARRIVED
            else:
                self.state = VehicleState.ACCELERATING

        elif self.state == VehicleState.ACCELERATING:
            if need_brake:
                self.state = VehicleState.DECELERATING
            elif ctx.speed >= ctx.v_max - 0.01:
                self.state = VehicleState.CRUISING

        elif self.state == VehicleState.CRUISING:
            if need_brake:
                self.state = VehicleState.DECELERATING
            elif ctx.v_max > ctx.speed + 0.5:
                # 限速提高了，可以加速
                self.state = VehicleState.ACCELERATING

        elif self.state == VehicleState.DECELERATING:
            if ctx.speed <= ctx.v_target + 0.01:
                if ctx.next_action == 'arrive' and ctx.dist_to_action < 5:
                    self.state = VehicleState.ARRIVED
                else:
                    # 完成减速，通过动作点后重新加速
                    if ctx.v_target < ctx.v_max - 0.5:
                        self.state = VehicleState.ACCELERATING
                    else:
                        self.state = VehicleState.CRUISING

    # =========================================================================
    # 位置更新
    # =========================================================================

    def _update_position(self):
        """更新位置"""
        ctx = self.context
        df = self.route_df
        p = self.params

        dist_step = ctx.speed * p.dt
        ctx.dist_total += dist_step
        ctx.dist_in_seg += dist_step

        # 跨段处理
        while ctx.seg_idx < len(df) - 1:
            seg_len = df.at[ctx.seg_idx, 'seg_len']
            if ctx.dist_in_seg < seg_len:
                break
            ctx.dist_in_seg -= seg_len
            ctx.seg_idx += 1

        # 插值计算当前位置（关键：从段起点开始插值）
        if ctx.seg_idx < len(df) - 1:
            seg_len = df.at[ctx.seg_idx, 'seg_len']
            if seg_len > 0:
                ratio = ctx.dist_in_seg / seg_len
                ratio = min(ratio, 1.0)  # 防止超出

                lat1 = df.at[ctx.seg_idx, 'Lat']
                lon1 = df.at[ctx.seg_idx, 'Lon']
                lat2 = df.at[ctx.seg_idx + 1, 'Lat']
                lon2 = df.at[ctx.seg_idx + 1, 'Lon']

                ctx.lat = lat1 + (lat2 - lat1) * ratio
                ctx.lon = lon1 + (lon2 - lon1) * ratio
            else:
                ctx.lat = df.at[ctx.seg_idx, 'Lat']
                ctx.lon = df.at[ctx.seg_idx, 'Lon']
        else:
            ctx.lat = df.at[len(df) - 1, 'Lat']
            ctx.lon = df.at[len(df) - 1, 'Lon']

    # =========================================================================
    # 主循环
    # =========================================================================

    def step(self) -> Dict[str, Any]:
        """
        执行一个时间步，返回当前状态数据

        Returns:
            包含当前状态信息的字典（列名与原版兼容）
        """
        # 1. 更新感知
        self._update_perception()

        # 2. 计算期望速度（与原版逻辑一致）
        self.context.speed_desired = self._compute_desired_speed()

        # 3. 更新速度（与原版 _update_speed 逻辑一致）
        self._update_speed()

        # 4. 更新位置
        self._update_position()

        # 5. 检查状态转移
        self._check_transitions()

        # 6. 返回数据（列名与原版兼容）
        return {
            'Lat': self.context.lat,
            'Lon': self.context.lon,
            'distance': self.context.dist_total,
            'speed': self.context.speed,
            'speed_desired': self.context.speed_desired,
            'speed_traffic': self.context.speed_traffic,
            'speed_base': self.context.speed_base,
            'next_action': self.context.next_action,
            'dist_to_next_action': self.context.dist_to_action,
            # 额外调试字段
            'state': self.state.name,
            'v_max': self.context.v_max,
            'v_target': self.context.v_target,
            'seg_idx': self.context.seg_idx,
        }

    def generate(self, departure_time: datetime, max_steps: int = 100000) -> pd.DataFrame:
        """
        生成完整驾驶工况

        Args:
            departure_time: 出发时间
            max_steps: 最大仿真步数（防止无限循环）

        Returns:
            包含驾驶工况的 DataFrame（列名与原版兼容）
        """
        records = []
        t = departure_time

        for step_num in range(max_steps):
            data = self.step()
            data['timestamp'] = t
            records.append(data)

            if self.state == VehicleState.ARRIVED:
                print(f"Arrived at step {step_num}, total distance: {self.context.dist_total/1000:.2f} km")
                break

            t += timedelta(seconds=self.params.dt)

            # 进度输出
            if step_num > 0 and step_num % 1000 == 0:
                print(f"Step {step_num} | state: {self.state.name} | "
                      f"v: {self.context.speed:.1f} m/s | "
                      f"dist: {self.context.dist_total/1000:.2f} km")

        # --- 最终减速停车（与原版一致）---
        final_lat = self.route_df.at[len(self.route_df) - 1, 'Lat']
        final_lon = self.route_df.at[len(self.route_df) - 1, 'Lon']

        while self.context.speed > 1e-3:
            # 减速
            self.context.speed = max(self.context.speed - self.params.a_dec * self.params.dt, 0.0)

            # 计算本步行驶距离
            dist_step = self.context.speed * self.params.dt
            self.context.dist_total += dist_step

            # 更新位置（向终点插值）
            dist_to_final = self._haversine(self.context.lat, self.context.lon, final_lat, final_lon)
            if dist_to_final > 0 and dist_step > 0:
                ratio = min(dist_step / dist_to_final, 1.0)
                self.context.lat = self.context.lat + (final_lat - self.context.lat) * ratio
                self.context.lon = self.context.lon + (final_lon - self.context.lon) * ratio

            # 记录数据
            records.append({
                'timestamp': t,
                'Lat': self.context.lat,
                'Lon': self.context.lon,
                'distance': self.context.dist_total,
                'speed': self.context.speed,
                'speed_desired': 0.0,
                'speed_traffic': self.route_df.at[len(self.route_df) - 1, 'TrafficSpeed'],
                'speed_base': self.route_df.at[len(self.route_df) - 1, 'BaseSpeed'],
                'next_action': 'arrive',
                'dist_to_next_action': max(0, dist_to_final - dist_step),
                'state': VehicleState.ARRIVED.name,
                'v_max': 0.0,
                'v_target': 0.0,
                'seg_idx': len(self.route_df) - 1,
            })

            t += timedelta(seconds=self.params.dt)

        # 最后一个点：速度为0，位置为终点
        records.append({
            'timestamp': t,
            'Lat': final_lat,
            'Lon': final_lon,
            'distance': self.context.dist_total,
            'speed': 0.0,
            'speed_desired': 0.0,
            'speed_traffic': self.route_df.at[len(self.route_df) - 1, 'TrafficSpeed'],
            'speed_base': self.route_df.at[len(self.route_df) - 1, 'BaseSpeed'],
            'next_action': 'arrive',
            'dist_to_next_action': 0.0,
            'state': VehicleState.ARRIVED.name,
            'v_max': 0.0,
            'v_target': 0.0,
            'seg_idx': len(self.route_df) - 1,
        })
        print("Arrived at destination.")

        df = pd.DataFrame(records)
        df['acc'] = df['speed'].diff().fillna(0.0) / self.params.dt
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # 速度平滑
        if self.params.smooth_speed and len(df) >= 5:
            win = min(len(df) // 2 * 2 + 1, 11)
            df['speed'] = savgol_filter(df['speed'], window_length=win, polyorder=3, mode='nearest')
            # 再次用v_cap限幅
            df['speed'] = df['speed'].clip(upper=self.params.v_cap)
            # 平滑后重新计算加速度
            df['acc'] = df['speed'].diff().fillna(0.0) / self.params.dt

        return df


# =============================================================================
# 兼容性包装类
# =============================================================================

class DrivingCycleGeneratorFSM:
    """
    状态机驾驶工况生成器的包装类

    提供与原 DrivingCycleGenerator 相同的接口，便于替换
    """

    def __init__(self):
        """初始化"""
        pass

    def generate_use_static_behaviour(
            self,
            route_df: pd.DataFrame,
            departure_time: datetime,
            v_cap: float = 25.0,
            v_roundabout_enter: float = 3.0,
            v_turn: float = 4.0,
            v_other_action: float = 5.0,
            a_acc: float = 0.58,
            a_dec: float = 0.83,
            dt: float = 1.0,
            v_cruise: float = 25.0,
            smooth_speed: bool = True
    ) -> pd.DataFrame:
        """
        生成驾驶工况（与原接口兼容）

        Args:
            route_df: 路线数据 DataFrame
            departure_time: 出发时间
            v_cap: 最大车速 (m/s)
            v_roundabout_enter: 环岛入口限速 (m/s)
            v_turn: 转弯限速 (m/s)
            v_other_action: 其他动作限速 (m/s)
            a_acc: 加速度 (m/s²)
            a_dec: 减速度 (m/s²)
            dt: 时间步长 (s)
            v_cruise: 巡航速度 (m/s)
            smooth_speed: 是否平滑速度曲线

        Returns:
            驾驶工况 DataFrame
        """
        if len(route_df) < 2:
            raise ValueError("route_df 至少需要两行经纬度数据")

        params = DrivingParams(
            v_cap=v_cap,
            v_cruise=v_cruise,
            v_turn=v_turn,
            v_roundabout=v_roundabout_enter,
            v_other_action=v_other_action,
            a_acc=a_acc,
            a_dec=a_dec,
            dt=dt,
            smooth_speed=smooth_speed,
        )

        fsm = DrivingCycleFSM(route_df, params)
        return fsm.generate(departure_time)

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间距离（米）- 兼容原接口"""
        return DrivingCycleFSM._haversine(lat1, lon1, lat2, lon2)


# =============================================================================
# 便捷函数
# =============================================================================

def generate_driving_cycle_fsm(
    route_df: pd.DataFrame,
    departure_time: datetime,
    **kwargs
) -> pd.DataFrame:
    """
    便捷函数：使用状态机生成驾驶工况

    Args:
        route_df: 路线数据 DataFrame
        departure_time: 出发时间
        **kwargs: 传递给 DrivingParams 的参数

    Returns:
        驾驶工况 DataFrame
    """
    params = DrivingParams(**kwargs)
    fsm = DrivingCycleFSM(route_df, params)
    return fsm.generate(departure_time)
