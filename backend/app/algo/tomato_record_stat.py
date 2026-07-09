import math
from collections import defaultdict
from collections.abc import Sequence
from datetime import timedelta

from app.models.tomato import TomatoTaskRecord


def calculate_metrics(records: Sequence[TomatoTaskRecord]) -> dict:
    """
    基于番茄钟日志计算长期观测指标（含同比趋势）。
    输入 records 按时间递增排序，覆盖最近15天左右。
    返回字典包含 summary, trend, volatility, daily_series。
    """
    if not records:
        return {}

    # ---------- 1. 按日期聚合 ----------
    daily = defaultdict(lambda: {"count": 0, "seconds": 0.0})
    for r in records:
        d = r.start_time.date()
        daily[d]["count"] += 1
        daily[d]["seconds"] += (r.finish_time - r.start_time).total_seconds()

    # 确定日期范围（连续补全缺失日期）
    all_dates = sorted(daily.keys())
    min_date = all_dates[0]
    max_date = all_dates[-1]

    date_list = []
    cur = min_date
    while cur <= max_date:
        date_list.append(cur)
        cur += timedelta(days=1)

    # 构建每日序列（按日期升序）
    daily_counts = []
    daily_hours = []  # 专注小时数
    for d in date_list:
        if d in daily:
            daily_counts.append(daily[d]["count"])
            daily_hours.append(daily[d]["seconds"] / 3600.0)
        else:
            daily_counts.append(0)
            daily_hours.append(0.0)

    total_days = len(date_list)
    total_count = sum(daily_counts)
    total_seconds = sum(daily[d]["seconds"] for d in daily)
    total_hours = total_seconds / 3600.0

    avg_daily_tomato = total_count / total_days if total_days else 0.0
    avg_daily_hours = total_hours / total_days if total_days else 0.0
    avg_tomato_minutes = (total_seconds / total_count / 60.0) if total_count else 0.0

    # ---------- 2. 周期同比辅助函数 ----------
    def get_period_stats(start_index, length):
        """从 date_list 末尾向前取，返回指定长度的统计值"""
        total_len = len(date_list)
        if start_index < 0 or start_index + length > total_len:
            return None
        sub_counts = daily_counts[start_index : start_index + length]
        sub_hours = daily_hours[start_index : start_index + length]
        return {
            "tomato_count": sum(sub_counts),
            "focus_hours": round(sum(sub_hours), 2),
            "avg_daily_tomato": round(sum(sub_counts) / length, 2),
            "avg_daily_hours": round(sum(sub_hours) / length, 2),
        }

    def calc_change(current, previous, key):
        if previous and previous.get(key, 0) != 0:
            return round((current[key] - previous[key]) / previous[key] * 100, 2)
        return 0.0

    # ---------- 3. 7天同比 ----------
    trend_7 = None
    date_len = len(date_list)
    if len(date_list) >= 14:
        cur_7 = get_period_stats(date_len-7, 7)  # 最近7天
        pre_7 = get_period_stats(date_len-14, 7)  # 前7天
        if cur_7 and pre_7:
            trend_7 = {
                "current": cur_7,
                "previous": pre_7,
                "change_percent": {
                    "tomato_count": calc_change(cur_7, pre_7, "tomato_count"),
                    "focus_hours": calc_change(cur_7, pre_7, "focus_hours"),
                    "avg_daily_tomato": calc_change(cur_7, pre_7, "avg_daily_tomato"),
                    "avg_daily_hours": calc_change(cur_7, pre_7, "avg_daily_hours"),
                },
            }

    # ---------- 4. 3天同比 ----------
    trend_3 = None
    if len(date_list) >= 6:
        cur_3 = get_period_stats(date_len-3, 3)
        pre_3 = get_period_stats(date_len-6, 3)
        if cur_3 and pre_3:
            trend_3 = {
                "current": cur_3,
                "previous": pre_3,
                "change_percent": {
                    "tomato_count": calc_change(cur_3, pre_3, "tomato_count"),
                    "focus_hours": calc_change(cur_3, pre_3, "focus_hours"),
                    "avg_daily_tomato": calc_change(cur_3, pre_3, "avg_daily_tomato"),
                    "avg_daily_hours": calc_change(cur_3, pre_3, "avg_daily_hours"),
                },
            }

    # ---------- 5. 波动性（基于全部天数） ----------
    if total_days > 1:
        mean = sum(daily_counts) / total_days
        variance = sum((x - mean) ** 2 for x in daily_counts) / (total_days - 1)  # 样本标准差
        std = math.sqrt(variance)
        cv = std / mean if mean else 0.0
    else:
        std = 0.0
        cv = 0.0

    # ---------- 6. 每日明细序列 ----------
    daily_series = [
        {"date": d.isoformat(), "tomato_count": c, "focus_hours": round(h, 2)}
        for d, c, h in zip(date_list, daily_counts, daily_hours, strict=True)
    ]

    # ---------- 7. 组装返回 ----------
    return {
        "summary": {
            "total_tomato_count": total_count,
            "total_focus_hours": round(total_hours, 2),
            "avg_tomato_duration_minutes": round(avg_tomato_minutes, 2),
            "total_days": total_days,
            "avg_daily_tomato": round(avg_daily_tomato, 2),
            "avg_daily_focus_hours": round(avg_daily_hours, 2),
        },
        "trend": {"last_7_days_vs_previous_7": trend_7, "last_3_days_vs_previous_3": trend_3},
        "volatility": {
            "std_daily_tomato": round(std, 2),
            "cv_daily_tomato": round(cv, 2),  # 变异系数（越小越稳定）
        },
        "daily_series": daily_series,
    }
