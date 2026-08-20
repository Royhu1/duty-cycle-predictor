"""
SRF Logger Data Downloader

从SRF平台下载车辆logger数据，保存为CSV文件。

依赖:
    - python-dotenv
    - cachecontrol
    - srf_client (SRF平台客户端)

这些依赖在实际调用下载方法时才需要，导入此模块不会触发依赖检查。
"""

from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple, Union, TYPE_CHECKING, Any

import numpy as np
import pandas as pd

import logging

logger = logging.getLogger(__name__)


def _haversine_series_m(latitude: np.ndarray, longitude: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Vectorized haversine distance between consecutive points (meters)."""
    lat = np.radians(latitude.astype(float))
    lon = np.radians(longitude.astype(float))

    dlat = np.diff(lat)
    dlon = np.diff(lon)

    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:-1]) * np.cos(lat[1:]) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    step = 6371000.0 * c
    step = np.insert(step, 0, 0.0)
    cum = np.cumsum(step)
    return step, cum


class SRFLoggerDataDownloader:
    """
    SRF平台Logger数据下载器

    用于根据车牌号和日期范围下载车辆logger数据。

    Example:
        downloader = SRFLoggerDataDownloader(api_key="your_api_key")

        # 或者从环境变量加载
        downloader = SRFLoggerDataDownloader()

        # 下载数据
        saved_files = downloader.download(
            vehicle_plate="AX15NLN",
            start_date="2019-03-15",
            end_date="2019-03-20",
            output_dir="data/AX15NLN",
            overwrite=True
        )
    """

    SRF_DEFAULT_ROOT = "https://data.csrf.ac.uk/api"

    def __init__(
        self,
        api_key: Optional[str] = None,
        srf_root: str = None,
        cache_dir: Optional[str] = None,
        verify_tls: bool = False
    ):
        """
        初始化下载器

        Args:
            api_key: SRF API密钥。如果不提供，将从环境变量 SRF_API_KEY 读取
            srf_root: SRF API根URL
            cache_dir: 缓存目录路径（可选）
            verify_tls: 是否验证TLS证书
        """
        # 延迟导入dotenv
        try:
            from dotenv import load_dotenv
            env_path = Path.cwd() / ".env"
            if env_path.exists():
                load_dotenv(env_path)
        except ImportError:
            pass  # dotenv not installed, skip loading .env

        self._api_key = api_key or os.environ.get("SRF_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Missing SRF API key. Provide api_key parameter or set SRF_API_KEY environment variable."
            )

        self._srf_root = srf_root or self.SRF_DEFAULT_ROOT
        self._cache_dir = cache_dir
        self._verify_tls = verify_tls
        self._client: Any = None

    def _get_client(self):
        """获取或创建SRF API客户端"""
        if self._client is None:
            # 延迟导入SRF客户端相关模块
            try:
                import cachecontrol.caches
                from srf_client import SRFData
            except ImportError as e:
                raise ImportError(
                    f"SRF client dependencies not installed: {e}. "
                    "Install with: pip install srf-client cachecontrol"
                )

            cache = None
            if self._cache_dir:
                cache = cachecontrol.caches.FileCache(self._cache_dir)

            self._client = SRFData(api_key=self._api_key, cache=cache, root=self._srf_root)
            self._client._session.verify = self._verify_tls

        return self._client

    def download(
        self,
        vehicle_plate: str,
        start_date: Union[str, dt.date],
        end_date: Union[str, dt.date],
        output_dir: Optional[str] = None,
        overwrite: bool = True,
        resolution_s: int = 1,
        min_distance_km: float = 0.0,
        speed_unit: str = "auto"
    ) -> List[Path]:
        """
        下载指定车辆在日期范围内的logger数据

        Args:
            vehicle_plate: 车牌号（如 "AX15NLN"）
            start_date: 开始日期（YYYY-MM-DD 或 YYYYMMDD 或 date对象）
            end_date: 结束日期（YYYY-MM-DD 或 YYYYMMDD 或 date对象）
            output_dir: 输出目录，默认为 data/{vehicle_plate}
            overwrite: 是否覆盖同名文件，默认为True
            resolution_s: 数据采样间隔（秒），默认1秒
            min_distance_km: 最小行程距离过滤（km），默认0（不过滤）
            speed_unit: 速度单位 ("auto", "kmph", "mps")

        Returns:
            保存的文件路径列表
        """
        # 延迟导入
        from srf_client import filter, paging, sort

        # 解析日期
        start = self._parse_date(start_date)
        end = self._parse_date(end_date)

        if end < start:
            raise ValueError("end_date must be >= start_date")

        # 设置输出目录
        if output_dir is None:
            output_dir = f"data/{vehicle_plate}"
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading data for {vehicle_plate}: {start} -> {end}")
        logger.info(f"Output directory: {out_path}")

        # 获取客户端和legs
        srf = self._get_client()
        vehicle, legs_iter = self._fetch_legs(srf, vehicle_plate, start, end)
        all_legs = list(paging.paged_items(legs_iter))

        logger.info(f"Found {len(all_legs)} legs in date range")

        # 按日期分组
        grouped = self._group_legs_by_date(all_legs, start, end, min_distance_km)

        # 下载并保存
        saved_files = []
        for d in sorted(grouped.keys()):
            legs = grouped[d]
            legs.sort(key=lambda x: self._leg_start_time_utc(x) or dt.datetime.max.replace(tzinfo=dt.timezone.utc))

            for i, leg in enumerate(legs, start=1):
                st = self._leg_start_time_utc(leg)
                et = self._leg_end_time_utc(leg)

                if st is None or et is None:
                    continue

                # 文件名: YYYYMMDDHHMM_YYYYMMDDHHMM.csv
                filename = f"{self._format_time(st)}_{self._format_time(et)}.csv"
                file_path = out_path / filename

                # 检查是否需要覆盖
                if file_path.exists() and not overwrite:
                    logger.info(f"Skip existing: {filename}")
                    continue

                try:
                    # 下载数据
                    raw_df = leg.get_data_frame(
                        data_types=["2", "7", "CVW", "VDHR", "EEC1", "CCVS"],
                        resolution=dt.timedelta(seconds=resolution_s),
                    )

                    if raw_df.empty:
                        logger.warning(f"Empty data for leg {d} #{i}")
                        continue

                    # 处理数据
                    processed_df = self._build_standard_df(raw_df, speed_unit=speed_unit)

                    # 保存
                    processed_df.to_csv(file_path, index=False)
                    saved_files.append(file_path)
                    logger.info(f"Saved: {filename}")

                except Exception as e:
                    logger.error(f"Failed to download leg {d} #{i}: {e}")

        logger.info(f"Download complete. Saved {len(saved_files)} files.")
        return saved_files

    def _parse_date(self, date_input: Union[str, dt.date]) -> dt.date:
        """解析日期输入"""
        if isinstance(date_input, dt.date):
            return date_input

        s = str(date_input).strip()
        if re.fullmatch(r"\d{8}", s):
            return dt.datetime.strptime(s, "%Y%m%d").date()
        return dt.date.fromisoformat(s)

    def _fetch_legs(self, srf, vehicle_plate: str, start_date: dt.date, end_date: dt.date):
        """从API获取legs"""
        from srf_client import filter, sort

        vehicle = srf.vehicles.get(obj_id=vehicle_plate)
        params = {
            "start_time": filter.between(
                dt.datetime.combine(start_date, dt.time.min, dt.timezone.utc),
                dt.datetime.combine(end_date, dt.time.max, dt.timezone.utc),
            ),
            "sort": sort.asc("startTime"),
        }
        legs = srf.legs.find_all(**params, **{"trip.vehicle.registration": vehicle.registration})
        return vehicle, legs

    def _group_legs_by_date(
        self,
        all_legs: list,
        start_date: dt.date,
        end_date: dt.date,
        min_distance_km: float
    ) -> dict:
        """按日期分组legs"""
        desired_dates = set(self._daterange(start_date, end_date))
        grouped = {}

        for leg in all_legs:
            st = self._leg_start_time_utc(leg)
            if st is None:
                continue

            d = st.date()
            if d not in desired_dates:
                continue

            # 过滤SRF LOGGER来源
            trip = getattr(leg, "trip", None)
            source = getattr(trip, "source", None) if trip is not None else None
            if source is not None and str(source) != "SRFLOGGER_V1":
                continue

            # 距离过滤
            if min_distance_km > 0:
                start_dist = getattr(leg, "start_distance", None)
                end_dist = getattr(leg, "end_distance", None)
                try:
                    if start_dist is not None and end_dist is not None:
                        dist_km = float(end_dist) - float(start_dist)
                        if dist_km < min_distance_km:
                            continue
                except Exception:
                    pass

            grouped.setdefault(d, []).append(leg)

        return grouped

    def _daterange(self, start: dt.date, end: dt.date) -> List[dt.date]:
        """生成日期范围"""
        out = []
        cur = start
        while cur <= end:
            out.append(cur)
            cur = cur + dt.timedelta(days=1)
        return out

    def _leg_start_time_utc(self, leg) -> Optional[dt.datetime]:
        """获取leg开始时间（UTC）"""
        for attr in ("startTime", "start_time", "start_time_utc"):
            t = self._safe_parse_datetime(getattr(leg, attr, None))
            if t is not None:
                if t.tzinfo is None:
                    return t.replace(tzinfo=dt.timezone.utc)
                return t.astimezone(dt.timezone.utc)
        return None

    def _leg_end_time_utc(self, leg) -> Optional[dt.datetime]:
        """获取leg结束时间（UTC）"""
        for attr in ("endTime", "end_time", "end_time_utc"):
            t = self._safe_parse_datetime(getattr(leg, attr, None))
            if t is not None:
                if t.tzinfo is None:
                    return t.replace(tzinfo=dt.timezone.utc)
                return t.astimezone(dt.timezone.utc)
        return None

    def _safe_parse_datetime(self, x) -> Optional[dt.datetime]:
        """安全解析datetime"""
        if x is None:
            return None
        if isinstance(x, dt.datetime):
            return x
        if isinstance(x, str):
            try:
                if x.endswith("Z"):
                    return dt.datetime.fromisoformat(x[:-1] + "+00:00")
                return dt.datetime.fromisoformat(x)
            except Exception:
                return None
        return None

    def _format_time(self, t: dt.datetime) -> str:
        """格式化时间为 YYYYMMDDHHMM"""
        if t.tzinfo is None:
            t = t.replace(tzinfo=dt.timezone.utc)
        t = t.astimezone(dt.timezone.utc)
        return t.strftime("%Y%m%d%H%M")

    def _build_standard_df(self, raw: pd.DataFrame, speed_unit: str = "auto") -> pd.DataFrame:
        """将原始数据转换为标准格式"""
        if not isinstance(raw.index, pd.DatetimeIndex):
            raise TypeError("Expected raw leg dataframe to have a DatetimeIndex")
        if raw.empty:
            raise ValueError("Empty SRF leg dataframe")

        # 列名映射
        lon_col = self._pick_col(raw, ["2 longitude"])
        lat_col = self._pick_col(raw, ["2 latitude"])
        bearing_col = self._pick_col(raw, ["2 bearing"])
        alt_col = self._pick_col(raw, ["2 altitude"])
        spd_col = self._pick_col(raw, ["CCVS wheel based vehicle speed"])
        gps_spd_col = self._pick_col(raw, ["2 speed"])
        eng_spd_col = self._pick_col(raw, ["EEC1 engine speed"])
        eng_trq_col = self._pick_col(raw, ["EEC1 actual engine percent torque"])
        mass_col = self._pick_col(raw, ["CVW gross combination vehicle weight"])

        out = pd.DataFrame(index=raw.index)
        out["UnixTime"] = self._to_unix_ms(raw.index)
        out["Longitude"] = self._ensure_numeric(raw[lon_col]) if lon_col else np.nan
        out["Latitude"] = self._ensure_numeric(raw[lat_col]) if lat_col else np.nan
        out["Bearing"] = self._ensure_numeric(raw[bearing_col]) if bearing_col else np.nan

        # 速度处理
        spd_kmph = pd.Series(np.nan, index=raw.index)
        if spd_col:
            speed_raw = raw[spd_col]
            if speed_unit == "kmph":
                spd_kmph = self._ensure_numeric(speed_raw)
            elif speed_unit == "mps":
                spd_kmph = self._ensure_numeric(speed_raw) * 3.6
            else:
                spd_kmph = self._auto_speed_to_kmph(speed_raw)
        elif gps_spd_col:
            spd_kmph = self._ensure_numeric(raw[gps_spd_col]) * 3.6

        out["Spd_Kmph_x"] = spd_kmph
        out["Spd_Kmph_y"] = spd_kmph

        out["EngSpd"] = self._ensure_numeric(raw[eng_spd_col]) if eng_spd_col else np.nan
        out["EngTrq"] = self._ensure_numeric(raw[eng_trq_col]) if eng_trq_col else np.nan
        out["MassKg"] = self._ensure_numeric(raw[mass_col]) if mass_col else np.nan
        out["elevation"] = self._ensure_numeric(raw[alt_col]) if alt_col else np.nan

        # 风速
        ws_col = self._pick_col(raw, ["7 wind speed"])
        wd_col = self._pick_col(raw, ["7 wind direction"])
        out["wind_speed_mps"] = self._ensure_numeric(raw[ws_col]) if ws_col else np.nan
        out["wind_dir"] = self._ensure_numeric(raw[wd_col]) if wd_col else np.nan

        # 刹车
        brake_pdl_col = self._pick_col(raw, ["CCVS brake pedal position"])
        brake_sw_col = self._pick_col(raw, ["CCVS brake switch"])

        if brake_pdl_col:
            out["BrkPedalPos"] = self._ensure_numeric(raw[brake_pdl_col]).fillna(0.0)
            out["BrakeSwitch"] = (out["BrkPedalPos"] > 0).astype(float)
        elif brake_sw_col:
            bs = raw[brake_sw_col]
            if bs.dtype == bool:
                bs = bs.astype(int)
            out["BrakeSwitch"] = self._ensure_numeric(bs).fillna(0.0)
            out["BrkPedalPos"] = out["BrakeSwitch"].fillna(0.0)
        else:
            out["BrkPedalPos"] = 0.0
            out["BrakeSwitch"] = 0.0

        # 距离计算
        lon = out["Longitude"].interpolate(limit_direction="both")
        lat = out["Latitude"].interpolate(limit_direction="both")
        if lat.notna().any() and lon.notna().any():
            step, cum = _haversine_series_m(lat.to_numpy(dtype=float), lon.to_numpy(dtype=float))
            out["distance_gps_per_step"] = step
            out["distance_gps"] = cum
        else:
            dist_col = self._pick_col(raw, ["VDHR hr total vehicle distance"])
            if dist_col:
                dist_km = self._ensure_numeric(raw[dist_col])
                first = dist_km.dropna().iloc[0] if dist_km.notna().any() else 0.0
                out["distance_gps"] = ((dist_km - first) * 1000.0).ffill().fillna(0.0).to_numpy()
                out["distance_gps_per_step"] = pd.Series(out["distance_gps"]).diff().fillna(0.0).to_numpy()
            else:
                dt_s = raw.index.to_series().diff().dt.total_seconds().fillna(0.0)
                step = ((out["Spd_Kmph_x"] / 3.6) * dt_s).fillna(0.0).to_numpy(dtype=float)
                out["distance_gps_per_step"] = step
                out["distance_gps"] = np.cumsum(step)

        out["Distance"] = out["distance_gps"]
        out["AccPedalPos"] = np.nan
        out["GearRatio"] = np.nan
        out["AirTemp"] = np.nan
        out["AirPressure"] = np.nan
        out["EngCoolant"] = np.nan
        out["FuelRate"] = np.nan
        out["FuelUse"] = np.nan
        out["CruiseSwitch"] = np.nan
        out["Acc_mps2"] = (out["Spd_Kmph_x"] / 3.6).diff().fillna(0.0)
        out["weather_desc"] = np.nan
        out["weather_type"] = np.nan
        out["traffic_speed_src"] = np.nan
        out["traffic_speed"] = np.nan
        out["road_gradient"] = np.nan

        # 列顺序
        cols = [
            "UnixTime", "Longitude", "Latitude", "Bearing",
            "Spd_Kmph_y", "Spd_Kmph_x", "Distance", "AccPedalPos",
            "BrkPedalPos", "EngSpd", "EngTrq", "GearRatio",
            "AirTemp", "AirPressure", "EngCoolant", "FuelRate",
            "FuelUse", "MassKg", "CruiseSwitch", "BrakeSwitch",
            "Acc_mps2", "wind_speed_mps", "wind_dir", "weather_desc",
            "elevation", "distance_gps_per_step", "distance_gps",
            "weather_type", "traffic_speed_src", "traffic_speed", "road_gradient",
        ]
        for c in cols:
            if c not in out.columns:
                out[c] = np.nan
        return out[cols]

    @staticmethod
    def _pick_col(df: pd.DataFrame, candidates: list) -> Optional[str]:
        """选择存在的列"""
        for c in candidates:
            if c in df.columns:
                return c
        return None

    @staticmethod
    def _to_unix_ms(index: pd.DatetimeIndex) -> np.ndarray:
        """转换为Unix毫秒时间戳"""
        idx = index
        if idx.tz is not None:
            idx = idx.tz_convert(dt.timezone.utc)
            idx = idx.tz_localize(None)
        return (idx.to_numpy(dtype="datetime64[ns]").astype("int64") // 1_000_000).astype("int64")

    @staticmethod
    def _ensure_numeric(s: pd.Series) -> pd.Series:
        """确保数值类型"""
        return pd.to_numeric(s, errors="coerce")

    @staticmethod
    def _auto_speed_to_kmph(speed_series: pd.Series) -> pd.Series:
        """自动判断速度单位并转换为km/h"""
        speed = pd.to_numeric(speed_series, errors="coerce")
        q95 = float(np.nanpercentile(speed.to_numpy(dtype=float), 95)) if speed.notna().any() else np.nan
        if np.isfinite(q95) and q95 < 60.0:
            return speed * 3.6
        return speed
