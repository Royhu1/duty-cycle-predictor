# DutyCyclePredictor 更新日志

本文件记录 DutyCyclePredictor 模块的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

---

## [0.1.3] - 2026-02-05

### 新增
- **路线有效性检验**：在 `predict()` 函数中添加 `_is_route_df_valid()` 检验
  - 检查起点终点直线距离是否 >= 5km
  - 距离过短的路线返回 `None`，避免无限循环
  - 文件：`duty_cycle_predictor.py` Line 43-83, 202-205
- **Haversine 距离计算**：添加 `_haversine_distance()` 辅助函数
  - 计算两个 GPS 坐标点之间的距离 (km)

### 变更
- `predict()` 返回类型从 `DutyCycle` 改为 `Optional[DutyCycle]`
  - 调用端需要处理返回 `None` 的情况

---

## [0.1.2] - 2026-02-02

### 修复
- **dist_2_next_action 计算错误**：初始值改为当前位置到当前段末端的剩余距离（原为 0）
  - 文件：`driving_cycle_generator.py` Line 137-143
- **v_cur=0, v_target=0 时车辆不启动**：重写 `compute_desired_speed_2_next_action` 逻辑
  - 新逻辑：`v_desired = min(v_cruise, sqrt(v_target² + 2 * a_dec * dist))`
  - 保证即使目标速度为 0，只要有足够距离，车辆仍会加速到巡航速度
  - 文件：`driving_cycle_generator.py` Line 230-256

---

## [0.1.1] - 2025-02-02

### 修复
- **预测提前终止问题**：使用多个 via points 时，预测不再在中间点提前停止
  - `here_api.py`：只为最终目的地分配 `arrive` action，忽略中间 section 的 `arrive`
  - `driving_cycle_generator.py`：增加位置验证，防止在路线中途因错误的 `arrive` 而终止

---

## [0.1.0] - 2025-01-21

### 新增
- **DutyCyclePredictor 类**：API 风格的行驶工况预测接口
  - `predict()`：从起终点坐标执行完整预测流程
  - `list_vehicle_types()`：列出可用车辆预设
  - `get_vehicle_params()`：获取车辆参数
  - `get_driving_behavior()`：获取驾驶行为参数
  - `version` / `version_info`：版本信息属性
- **VehicleParams 数据类**：车辆物理与动力系统参数
  - 质量、迎风面积、风阻系数、滚动阻力系数
  - 传动效率、发动机效率、燃料热值
  - `to_dict()` / `from_dict()` 序列化方法
- **DrivingBehavior 数据类**：驾驶行为参数
  - 速度限制（v_cap, v_cruise, v_turn, v_roundabout_enter）
  - 加减速限制（a_acc, a_dec）
  - 仿真参数（dt, smooth_speed）
- **PredictionResult 数据类**：结果容器
  - 核心输出：speed_profile, gradient_profile, energy_profile
  - 预留字段：weather_profile, auxiliary_profile（未来扩展）
  - 汇总统计字典
  - `to_dict()`, `to_json()`, `save()` 方法
- **车辆预设**：4 种内置车型
  - default_truck（5000 kg，90 km/h）
  - light_truck（3500 kg，100 km/h）
  - heavy_truck（18000 kg，80 km/h）
  - delivery_van（2500 kg，110 km/h）
- **模块结构**：
  - `params.py`：参数类与预设
  - `models.py`：结果数据类
  - `duty_cycle_predictor.py`：主预测器类
  - `version.py`：版本信息
- **便捷函数**：`quick_predict()` 快速预测

### 架构
```
输入: origin, destination, vehicle_type
    ↓
[HERE API] → 路线航点
    ↓
[SRF API] → 高程数据（可选）
    ↓
[DrivingCycleGenerator] → 速度曲线
[GradientCycleGenerator] → 坡度曲线
    ↓
[LVD] → 能耗/油耗曲线
    ↓
输出: PredictionResult
```

---

## [未发布]

### 计划中
- 天气 API 集成（weather_profile）
- 附属负载建模（auxiliary_profile）
- 电动车支持
- 多段行程规划

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 0.1.3 | 2026-02-05 | 添加路线有效性检验，防止短距离路线导致无限循环 |
| 0.1.2 | 2026-02-02 | 修复 dist_2_next_action 计算和 v_cur=0 时不动的问题 |
| 0.1.1 | 2025-02-02 | 修复多 via points 路线预测提前终止问题 |
| 0.1.0 | 2025-01-21 | 初始版本，核心预测功能 |
