import random


class RowingModule:
    def __init__(self, name: str, spm_sequence: list[int], resistance_offset: int, stage_tags: list[str]):
        """
        :param name: 模块名称
        :param spm_sequence: 前段（不含末尾恢复分钟）每分钟的SPM列表，长度决定前段时长
        :param resistance_offset: 相对于阶段基准偏移的额外偏移值（整数）
        :param stage_tags: 允许出现的阶段标签，如 ['ascend', 'peak', 'descend']
        """
        self.name = name
        self.spm_sequence = spm_sequence
        self.resistance_offset = resistance_offset
        self.stage_tags = stage_tags
        self.recovery_spm = 20  # 末尾恢复分钟固定频率
        self.duration = len(spm_sequence) + 1  # 总时长 = 前段分钟数 + 1（恢复）

    def get_spm_pattern(self) -> list[int]:
        """返回完整的SPM序列（前段 + 恢复分钟）"""
        return self.spm_sequence + [self.recovery_spm]

    def get_resistance(self, base: int, phase_offset: int) -> int:
        """计算该模块的绝对阻力值，并限制在1~31之间"""
        raw = base + phase_offset + self.resistance_offset
        return max(1, min(31, raw))


def build_module_pool() -> list[RowingModule]:
    modules = []

    # ---- 力量流 (高阻, +1偏移) ----
    modules.append(RowingModule("短距重锤", [20, 20], +2, ["peak"]))
    modules.append(RowingModule("力量爬坡", [20, 21, 22], +2, ["peak"]))
    modules.append(RowingModule("重型间歇", [19, 21, 21, 20], +2, ["peak"]))
    # 新增力量耐力变种
    modules.append(RowingModule("力量持久", [19, 21, 21], +2, ["peak"]))

    # ---- 速度/节奏流 (低阻, -1偏移) ----
    modules.append(RowingModule("极速双响", [26, 27], -2, ["ascend", "descend"]))
    modules.append(RowingModule("节奏湍流", [24, 26, 25], -2, ["ascend", "descend"]))
    modules.append(RowingModule("高速耐力", [22, 24, 26, 24], -2, ["ascend", "descend"]))
    modules.append(RowingModule("轻快踩踏", [26, 26, 26], -2, ["ascend", "descend"]))
    # 新增：高频短促
    modules.append(RowingModule("高频脉冲", [27, 27], -2, ["ascend", "descend"]))

    # ---- 耐力/渐变流 (中阻, 0偏移) ----
    modules.append(RowingModule("稳态阶梯", [22, 24, 26], 0, ["ascend", "peak", "descend"]))
    modules.append(RowingModule("长呼吸窗", [22, 24, 24, 22], 0, ["ascend", "peak", "descend"]))
    modules.append(RowingModule("温和金字塔", [21, 23, 25, 21], 0, ["ascend", "peak", "descend"]))
    # 新增低阻耐力（适合上升/下降）
    modules.append(RowingModule("低阻巡航", [24, 24, 24], -2, ["ascend", "descend"]))
    # 新增高阻耐力（适合峰值）
    modules.append(RowingModule("高阻巡航", [20, 21, 22, 21], +2, ["peak"]))

    # ---- 技术/特效流 (偏移不定) ----
    modules.append(RowingModule("暂停式冥想", [20, 20], 0, ["peak"]))  # 虽慢但核心紧张
    modules.append(RowingModule("交替发力", [22, 22, 22], 0, ["ascend", "peak", "descend"]))
    modules.append(RowingModule("闭眼平衡", [24, 24, 24, 24], -2, ["descend"]))
    modules.append(RowingModule("呼吸控制", [22, 22], -2, ["ascend", "descend"]))

    return modules


def generate_rowing_workout(
    target_minutes: int = 20,
    base_resistance: int = 14,
    warmup_spm: tuple = (20, 20, 22),
    warmup_resistance_offset: int = -4,  # 热身相对基准的偏移（例如0表示直接用base）
    ascend_offset: int = -2,  # 上升期相对基准的偏移
    peak_offset: int = +4,  # 峰值期相对基准的偏移
    descend_offset: int = -2,  # 下降期相对基准的偏移
    phase_ratios: tuple[float, float, float] = (0.30, 0.40, 0.30),  # 上升/峰值/下降时长比例
) -> tuple[list[int], list[int]]:
    """
    生成训练计划
    :return: (spm_list, resistance_list) 每分钟的数据
    """
    # ----- 初始化结果 -----
    spm_result = []
    res_result = []

    # ----- 固定热身 -----
    warmup_res = base_resistance + warmup_resistance_offset
    warmup_res = max(1, min(31, warmup_res))
    for spm in warmup_spm:
        spm_result.append(spm)
        res_result.append(warmup_res)

    total_time = len(warmup_spm)  # 热身分钟数，固定为3, 不计入总时长

    # ----- 计算各阶段目标时长（主训部分）-----
    ascend_target = int(target_minutes * phase_ratios[0])
    peak_target = int(target_minutes * phase_ratios[1])
    descend_target = target_minutes - ascend_target - peak_target  # 剩余全给下降

    # 阶段配置
    phases = [
        ("ascend", ascend_offset, ascend_target),
        ("peak", peak_offset, peak_target),
        ("descend", descend_offset, descend_target),
    ]

    # 获取全部模块，并建立按阶段标签索引
    all_modules = build_module_pool()
    # 按阶段分组（用于快速过滤）
    phase_modules = {tag: [] for tag in ["ascend", "peak", "descend"]}
    for m in all_modules:
        for tag in m.stage_tags:
            phase_modules[tag].append(m)

    # ----- 按顺序填充各阶段 -----
    for phase_name, phase_off, phase_goal in phases:
        # 该阶段剩余需填充的分钟数
        phase_remaining = phase_goal

        # 当剩余时间大于0且总时间未超过目标（或即使超过也不影响，但为了保持阶段顺序，我们只在此阶段内填充）
        while phase_remaining > 0:
            # 过滤出时长 <= phase_remaining 的模块
            candidates = [m for m in phase_modules.get(phase_name, []) if m.duration <= phase_remaining]
            if not candidates:
                break  # 剩余时间不足以放入任何模块，结束本阶段

            # 随机抽取一个模块（可加权，此处简单等权）
            chosen = random.choice(candidates)

            # 计算该模块的阻力
            resistance = chosen.get_resistance(base_resistance, phase_off)

            # 展开SPM序列
            for spm in chosen.get_spm_pattern():
                spm_result.append(spm)
                res_result.append(resistance)
                total_time += 1
                phase_remaining -= 1
                # 注意：phase_remaining 减去了模块的总时长（包括恢复分钟）

    # ----- 最后，如果总时间仍小于目标，在下降阶段继续补充（保持下降阻力）-----
    while total_time < target_minutes:
        # 从下降阶段候选池中挑选
        candidates = phase_modules.get("descend", [])
        # 过滤出时长 <= (target_minutes - total_time) 的模块，但若剩余小于最短模块，则强行使用最短模块并截断？但我们可以继续抽取，即使超出也无妨。
        # 为简化，直接随机选一个下降阶段模块
        if not candidates:
            # 如果下降池为空（理论上不会），使用任意模块
            candidates = all_modules
        chosen = random.choice(candidates)
        # 计算下降阶段阻力
        resistance = chosen.get_resistance(base_resistance, descend_offset)
        for spm in chosen.get_spm_pattern():
            spm_result.append(spm)
            res_result.append(resistance)
            total_time += 1
        # 注意：上述循环会完整添加一个模块，可能会超出不少。如果希望不要超出太多，可以限制添加分钟数。

    return spm_result, res_result
