<template>
    <div class="tomato-trend-panel">
        <!-- 加载状态 -->
        <div v-if="loading" class="loading-container">
            <div class="loading-spinner"></div>
            <span class="loading-text">正在加载番茄钟数据...</span>
        </div>

        <!-- 错误状态 -->
        <div v-else-if="error" class="error-container">
            <div class="error-icon">⚠️</div>
            <p class="error-message">{{ error }}</p>
            <button class="retry-btn" @click="fetchData">重新加载</button>
        </div>

        <!-- 正常内容 -->
        <template v-else-if="data">
            <!-- 面板标题 -->
            <div class="panel-header">
                <h2 class="panel-title">🍅 番茄钟长期趋势</h2>
                <span class="panel-subtitle">数据统计截止至最新记录</span>
            </div>

            <!-- 摘要指标卡片行 -->
            <div class="summary-cards">
                <div class="summary-card card-tomato">
                    <div class="card-icon">🍅</div>
                    <div class="card-value">{{ data.summary.total_tomato_count }}</div>
                    <div class="card-label">总番茄数</div>
                    <div class="card-sub">个</div>
                </div>
                <div class="summary-card card-focus">
                    <div class="card-icon">⏱️</div>
                    <div class="card-value">{{ formatHours(data.summary.total_focus_hours) }}</div>
                    <div class="card-label">总专注时长</div>
                    <div class="card-sub">小时</div>
                </div>
                <div class="summary-card card-avg-duration">
                    <div class="card-icon">⏲️</div>
                    <div class="card-value">{{ formatDecimal(data.summary.avg_tomato_duration_minutes) }}</div>
                    <div class="card-label">平均番茄时长</div>
                    <div class="card-sub">分钟/个</div>
                </div>
                <div class="summary-card card-days">
                    <div class="card-icon">📅</div>
                    <div class="card-value">{{ data.summary.total_days }}</div>
                    <div class="card-label">总天数</div>
                    <div class="card-sub">天</div>
                </div>
                <div class="summary-card card-avg-tomato">
                    <div class="card-icon">📊</div>
                    <div class="card-value">{{ formatDecimal(data.summary.avg_daily_tomato) }}</div>
                    <div class="card-label">日均番茄数</div>
                    <div class="card-sub">个/天</div>
                </div>
                <div class="summary-card card-avg-hours">
                    <div class="card-icon">📈</div>
                    <div class="card-value">{{ formatDecimal(data.summary.avg_daily_focus_hours) }}</div>
                    <div class="card-label">日均专注时长</div>
                    <div class="card-sub">小时/天</div>
                </div>
            </div>

            <!-- 趋势对比区域 -->
            <div class="trend-section">
                <h3 class="section-title">📉 趋势对比</h3>
                <div class="trend-cards">
                    <!-- 7天对比 -->
                    <div class="trend-card">
                        <div class="trend-card-header">
                            <span class="trend-badge badge-week">7天</span>
                            <span class="trend-period">最近7天 vs 前7天</span>
                        </div>
                        <div class="trend-comparisons">
                            <div class="trend-item">
                                <span class="trend-item-label">🍅 番茄数</span>
                                <div class="trend-item-values">
                                    <span class="current-value">{{
                                        data.trend.last_7_days_vs_previous_7.current.tomato_count }}</span>
                                    <span class="vs-separator">vs</span>
                                    <span class="previous-value">{{
                                        data.trend.last_7_days_vs_previous_7.previous.tomato_count }}</span>
                                    <span class="change-tag"
                                        :class="getChangeClass(data.trend.last_7_days_vs_previous_7.change_percent.tomato_count)">
                                        {{
                                            formatChangePercent(data.trend.last_7_days_vs_previous_7.change_percent.tomato_count)
                                        }}
                                    </span>
                                </div>
                            </div>
                            <div class="trend-item">
                                <span class="trend-item-label">⏱️ 专注时长</span>
                                <div class="trend-item-values">
                                    <span class="current-value">{{
                                        formatHours(data.trend.last_7_days_vs_previous_7.current.focus_hours) }}h</span>
                                    <span class="vs-separator">vs</span>
                                    <span class="previous-value">{{
                                        formatHours(data.trend.last_7_days_vs_previous_7.previous.focus_hours)
                                    }}h</span>
                                    <span class="change-tag"
                                        :class="getChangeClass(data.trend.last_7_days_vs_previous_7.change_percent.focus_hours)">
                                        {{
                                            formatChangePercent(data.trend.last_7_days_vs_previous_7.change_percent.focus_hours)
                                        }}
                                    </span>
                                </div>
                            </div>
                            <div class="trend-item">
                                <span class="trend-item-label">📊 日均番茄</span>
                                <div class="trend-item-values">
                                    <span class="current-value">{{
                                        formatDecimal(data.trend.last_7_days_vs_previous_7.current.avg_daily_tomato)
                                    }}</span>
                                    <span class="vs-separator">vs</span>
                                    <span class="previous-value">{{
                                        formatDecimal(data.trend.last_7_days_vs_previous_7.previous.avg_daily_tomato)
                                    }}</span>
                                    <span class="change-tag"
                                        :class="getChangeClass(data.trend.last_7_days_vs_previous_7.change_percent.avg_daily_tomato)">
                                        {{
                                            formatChangePercent(data.trend.last_7_days_vs_previous_7.change_percent.avg_daily_tomato)
                                        }}
                                    </span>
                                </div>
                            </div>
                            <div class="trend-item">
                                <span class="trend-item-label">📈 日均时长</span>
                                <div class="trend-item-values">
                                    <span class="current-value">{{
                                        formatDecimal(data.trend.last_7_days_vs_previous_7.current.avg_daily_hours)
                                    }}h</span>
                                    <span class="vs-separator">vs</span>
                                    <span class="previous-value">{{
                                        formatDecimal(data.trend.last_7_days_vs_previous_7.previous.avg_daily_hours)
                                    }}h</span>
                                    <span class="change-tag"
                                        :class="getChangeClass(data.trend.last_7_days_vs_previous_7.change_percent.avg_daily_hours)">
                                        {{
                                            formatChangePercent(data.trend.last_7_days_vs_previous_7.change_percent.avg_daily_hours)
                                        }}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 3天对比 -->
                    <div v-if="data.trend.last_3_days_vs_previous_3" class="trend-card">
                        <div class="trend-card-header">
                            <span class="trend-badge badge-3day">3天</span>
                            <span class="trend-period">最近3天 vs 前3天</span>
                        </div>
                        <div class="trend-comparisons">
                            <div class="trend-item">
                                <span class="trend-item-label">🍅 番茄数</span>
                                <div class="trend-item-values">
                                    <span class="current-value">{{
                                        data.trend.last_3_days_vs_previous_3.current.tomato_count }}</span>
                                    <span class="vs-separator">vs</span>
                                    <span class="previous-value">{{
                                        data.trend.last_3_days_vs_previous_3.previous.tomato_count }}</span>
                                    <span class="change-tag"
                                        :class="getChangeClass(data.trend.last_3_days_vs_previous_3.change_percent.tomato_count)">
                                        {{
                                            formatChangePercent(data.trend.last_3_days_vs_previous_3.change_percent.tomato_count)
                                        }}
                                    </span>
                                </div>
                            </div>
                            <div class="trend-item">
                                <span class="trend-item-label">⏱️ 专注时长</span>
                                <div class="trend-item-values">
                                    <span class="current-value">{{
                                        formatHours(data.trend.last_3_days_vs_previous_3.current.focus_hours) }}h</span>
                                    <span class="vs-separator">vs</span>
                                    <span class="previous-value">{{
                                        formatHours(data.trend.last_3_days_vs_previous_3.previous.focus_hours)
                                    }}h</span>
                                    <span class="change-tag"
                                        :class="getChangeClass(data.trend.last_3_days_vs_previous_3.change_percent.focus_hours)">
                                        {{
                                            formatChangePercent(data.trend.last_3_days_vs_previous_3.change_percent.focus_hours)
                                        }}
                                    </span>
                                </div>
                            </div>
                            <div class="trend-item">
                                <span class="trend-item-label">📊 日均番茄</span>
                                <div class="trend-item-values">
                                    <span class="current-value">{{
                                        formatDecimal(data.trend.last_3_days_vs_previous_3.current.avg_daily_tomato)
                                    }}</span>
                                    <span class="vs-separator">vs</span>
                                    <span class="previous-value">{{
                                        formatDecimal(data.trend.last_3_days_vs_previous_3.previous.avg_daily_tomato)
                                    }}</span>
                                    <span class="change-tag"
                                        :class="getChangeClass(data.trend.last_3_days_vs_previous_3.change_percent.avg_daily_tomato)">
                                        {{
                                            formatChangePercent(data.trend.last_3_days_vs_previous_3.change_percent.avg_daily_tomato)
                                        }}
                                    </span>
                                </div>
                            </div>
                            <div class="trend-item">
                                <span class="trend-item-label">📈 日均时长</span>
                                <div class="trend-item-values">
                                    <span class="current-value">{{
                                        formatDecimal(data.trend.last_3_days_vs_previous_3.current.avg_daily_hours)
                                    }}h</span>
                                    <span class="vs-separator">vs</span>
                                    <span class="previous-value">{{
                                        formatDecimal(data.trend.last_3_days_vs_previous_3.previous.avg_daily_hours)
                                    }}h</span>
                                    <span class="change-tag"
                                        :class="getChangeClass(data.trend.last_3_days_vs_previous_3.change_percent.avg_daily_hours)">
                                        {{
                                            formatChangePercent(data.trend.last_3_days_vs_previous_3.change_percent.avg_daily_hours)
                                        }}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 每日趋势折线图 -->
            <div class="chart-section">
                <h3 class="section-title">📅 每日趋势</h3>
                <div class="chart-wrapper">
                    <canvas ref="chartCanvas"></canvas>
                </div>
                <div v-if="data.volatility" class="volatility-info">
                    <span class="volatility-item">
                        <span class="volatility-label">标准差 (日番茄数)</span>
                        <span class="volatility-value">{{ formatDecimal(data.volatility.std_daily_tomato) }}</span>
                    </span>
                    <span class="volatility-divider">|</span>
                    <span class="volatility-item">
                        <span class="volatility-label">变异系数</span>
                        <span class="volatility-value">{{ formatDecimal(data.volatility.cv_daily_tomato) }}</span>
                    </span>
                    <span class="volatility-tip">
                        {{ getVolatilityTip(data.volatility.cv_daily_tomato) }}
                    </span>
                </div>
            </div>
        </template>

        <!-- 空数据状态 -->
        <div v-else class="empty-container">
            <div class="empty-icon">📭</div>
            <p class="empty-text">暂无番茄钟数据</p>
            <p class="empty-hint">开始您的第一个番茄钟吧！</p>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import axios from 'axios'
import {
    Chart,
    LineController,
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Tooltip,
    Legend,
    Filler,
    type ChartConfiguration,
    type ChartDataset
} from 'chart.js'

// ==================== Chart.js 注册 ====================
Chart.register(
    LineController,
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Tooltip,
    Legend,
    Filler
)

// ==================== TypeScript 类型定义 ====================
interface TrendPeriodData {
    tomato_count: number
    focus_hours: number
    avg_daily_tomato: number
    avg_daily_hours: number
}

interface TrendChangePercent {
    tomato_count: number
    focus_hours: number
    avg_daily_tomato: number
    avg_daily_hours: number
}

interface TrendComparison {
    current: TrendPeriodData
    previous: TrendPeriodData
    change_percent: TrendChangePercent
}

interface DailySeriesItem {
    date: string
    tomato_count: number
    focus_hours: number
}

interface TomatoSummary {
    total_tomato_count: number
    total_focus_hours: number
    avg_tomato_duration_minutes: number
    total_days: number
    avg_daily_tomato: number
    avg_daily_focus_hours: number
}

interface VolatilityData {
    std_daily_tomato: number
    cv_daily_tomato: number
}

interface TomatoTrendData {
    summary: TomatoSummary
    trend: {
        last_7_days_vs_previous_7: TrendComparison
        last_3_days_vs_previous_3?: TrendComparison
    }
    volatility?: VolatilityData
    daily_series: DailySeriesItem[]
}

// ==================== 响应式状态 ====================
const loading = ref<boolean>(true)
const error = ref<string | null>(null)
const data = ref<TomatoTrendData | null>(null)
const chartCanvas = ref<HTMLCanvasElement | null>(null)
const chartInstance = ref<Chart<'line'> | null>(null)

// ==================== 工具函数 ====================
function formatHours(hours: number): string {
    return hours.toFixed(1)
}

function formatDecimal(value: number): string {
    return value.toFixed(1)
}

function formatChangePercent(percent: number): string {
    if (percent > 0) return `↑ ${percent.toFixed(1)}%`
    if (percent < 0) return `↓ ${Math.abs(percent).toFixed(1)}%`
    return `→ 0%`
}

function getChangeClass(percent: number): string {
    if (percent > 0) return 'change-positive'
    if (percent < 0) return 'change-negative'
    return 'change-neutral'
}

function getVolatilityTip(cv: number): string {
    if (cv < 0.15) return '波动较小，状态稳定'
    if (cv < 0.35) return '波动适中，属于正常范围'
    return '波动较大，建议保持规律'
}

function formatDateLabel(dateStr: string): string {
    const parts = dateStr.split('-')
    if (parts.length === 3) {
        return `${parts[1]}/${parts[2]}`
    }
    return dateStr
}

// ==================== 图表相关 ====================
function createChart(dailySeries: DailySeriesItem[]): void {
    console.log("创建图表", chartCanvas, chartCanvas.value)
    if (!chartCanvas.value) return

    // 销毁旧图表实例
    if (chartInstance.value) {
        chartInstance.value.destroy()
        chartInstance.value = null
    }

    const labels = dailySeries.map((item) => formatDateLabel(item.date))
    const tomatoData = dailySeries.map((item) => item.tomato_count)
    const focusHoursData = dailySeries.map((item) => item.focus_hours)

    const ctx = chartCanvas.value.getContext('2d')
    if (!ctx) return

    const config: ChartConfiguration<'line'> = {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: '番茄数 (个)',
                    data: tomatoData,
                    borderColor: '#FF6B6B',
                    backgroundColor: 'rgba(255, 107, 107, 0.1)',
                    borderWidth: 2.5,
                    pointBackgroundColor: '#FF6B6B',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    pointHoverBackgroundColor: '#FF6B6B',
                    tension: 0.35,
                    fill: true,
                    yAxisID: 'y',
                    order: 1
                } as ChartDataset<'line', number[]>,
                {
                    label: '专注时长 (小时)',
                    data: focusHoursData,
                    borderColor: '#4ECDC4',
                    backgroundColor: 'rgba(78, 205, 196, 0.08)',
                    borderWidth: 2.5,
                    pointBackgroundColor: '#4ECDC4',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    pointHoverBackgroundColor: '#4ECDC4',
                    tension: 0.35,
                    fill: true,
                    yAxisID: 'y1',
                    order: 2
                } as ChartDataset<'line', number[]>
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'top',
                    align: 'end',
                    labels: {
                        usePointStyle: true,
                        pointStyleWidth: 8,
                        padding: 20,
                        font: {
                            size: 12,
                            family:
                                "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
                        },
                        color: '#555'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(44, 62, 80, 0.92)',
                    titleFont: { size: 13 },
                    bodyFont: { size: 12 },
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: true,
                    boxPadding: 4,
                    callbacks: {
                        title(tooltipItems) {
                            const idx = tooltipItems[0]?.dataIndex
                            if (idx !== undefined && idx >= 0 && idx < dailySeries.length) {
                                return dailySeries[idx].date
                            }
                            return tooltipItems[0]?.label || ''
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: { size: 11 },
                        color: '#888',
                        maxRotation: 45,
                        minRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 12
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: '番茄数 (个)',
                        font: { size: 11 },
                        color: '#FF6B6B'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: { size: 11 },
                        color: '#888',
                        stepSize: 1,
                        callback(value) {
                            return Math.round(Number(value))
                        }
                    },
                    beginAtZero: true,
                    suggestedMax: Math.ceil(Math.max(...tomatoData) * 1.2) || 10
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: '专注时长 (小时)',
                        font: { size: 11 },
                        color: '#4ECDC4'
                    },
                    grid: {
                        drawOnChartArea: false
                    },
                    ticks: {
                        font: { size: 11 },
                        color: '#888',
                        callback(value) {
                            return Number(value).toFixed(1) + 'h'
                        }
                    },
                    beginAtZero: true,
                    suggestedMax: Math.ceil(Math.max(...focusHoursData) * 1.25) || 5
                }
            }
        }
    }

    chartInstance.value = new Chart(ctx, config)
}

function destroyChart(): void {
    if (chartInstance.value) {
        chartInstance.value.destroy()
        chartInstance.value = null
    }
}

// ==================== 数据获取 ====================
async function fetchData(): Promise<void> {
    loading.value = true
    error.value = null

    try {
        const response = await axios.get<TomatoTrendData>('/summary/tomato')
        if (response.data && response.data.summary) {
            data.value = response.data
            // ✅ 关键：立即结束 loading 状态，让 canvas 渲染出来
            loading.value = false

            // 等待 Vue 更新 DOM
            await nextTick()
            if (response.data.daily_series && response.data.daily_series.length > 0) {
                createChart(response.data.daily_series)
            }
        } else {
            data.value = null
            loading.value = false
        }
    } catch (err: unknown) {
        console.error('获取番茄钟数据失败:', err)
        if (axios.isAxiosError(err)) {
            if (err.response) {
                error.value = `请求失败 (${err.response.status}): ${err.response.data?.message || '服务器错误，请稍后重试'
                    }`
            } else if (err.request) {
                error.value = '网络连接失败，请检查网络后重试'
            } else {
                error.value = err.message || '请求异常，请稍后重试'
            }
        } else {
            error.value = '未知错误，请稍后重试'
        }
        data.value = null
        loading.value = false
    }
}

// ==================== 生命周期 ====================
onMounted(() => {
    fetchData()
})

onUnmounted(() => {
    destroyChart()
})

// 监听数据变化，更新图表（当daily_series变化时）
watch(
    () => data.value?.daily_series,
    (newSeries) => {
        if (newSeries && newSeries.length > 0 && chartCanvas.value) {
            nextTick(() => {
                createChart(newSeries)
            })
        }
    },
    { deep: true }
)
</script>

<style scoped>
/* ==================== 容器基础样式 ==================== */
.tomato-trend-panel {
    --tomato-red: #ff6b6b;
    --tomato-red-light: #fff0f0;
    --tomato-red-dark: #e55a5a;
    --focus-teal: #4ecdc4;
    --focus-teal-light: #e8faf8;
    --text-primary: #2c3e50;
    --text-secondary: #666;
    --text-muted: #999;
    --bg-card: #ffffff;
    --bg-page: #f8f9fb;
    --border-color: #eef0f4;
    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
    --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.07), 0 2px 4px rgba(0, 0, 0, 0.04);
    --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.09), 0 4px 8px rgba(0, 0, 0, 0.04);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --green: #27ae60;
    --green-bg: #eafaf1;
    --red: #e74c3c;
    --red-bg: #fdedec;
    --neutral: #95a5a6;
    --neutral-bg: #f5f6f7;
    --transition: 0.2s ease;

    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
        sans-serif;
    color: var(--text-primary);
    background: var(--bg-page);
    border-radius: var(--radius-lg);
    padding: 24px 28px;
    max-width: 1100px;
    margin: 0 auto;
    box-sizing: border-box;
}

/* ==================== 加载状态 ==================== */
.loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    gap: 16px;
}

.loading-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid var(--border-color);
    border-top-color: var(--tomato-red);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

.loading-text {
    color: var(--text-muted);
    font-size: 14px;
}

/* ==================== 错误状态 ==================== */
.error-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 50px 20px;
    gap: 12px;
}

.error-icon {
    font-size: 48px;
}

.error-message {
    color: var(--text-secondary);
    font-size: 14px;
    text-align: center;
    margin: 0;
    max-width: 400px;
    line-height: 1.5;
}

.retry-btn {
    margin-top: 8px;
    padding: 10px 24px;
    background: var(--tomato-red);
    color: #fff;
    border: none;
    border-radius: var(--radius-sm);
    font-size: 14px;
    cursor: pointer;
    transition: background var(--transition), transform var(--transition);
}

.retry-btn:hover {
    background: var(--tomato-red-dark);
    transform: translateY(-1px);
}

.retry-btn:active {
    transform: translateY(0);
}

/* ==================== 空数据状态 ==================== */
.empty-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    gap: 8px;
}

.empty-icon {
    font-size: 52px;
}

.empty-text {
    font-size: 16px;
    color: var(--text-secondary);
    margin: 0;
    font-weight: 500;
}

.empty-hint {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
}

/* ==================== 面板标题 ==================== */
.panel-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 22px;
    flex-wrap: wrap;
    gap: 8px;
}

.panel-title {
    margin: 0;
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.3px;
}

.panel-subtitle {
    font-size: 12px;
    color: var(--text-muted);
}

/* ==================== 摘要卡片网格 ==================== */
.summary-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 14px;
    margin-bottom: 24px;
}

.summary-card {
    background: var(--bg-card);
    border-radius: var(--radius-md);
    padding: 18px 16px;
    box-shadow: var(--shadow-sm);
    text-align: center;
    transition: box-shadow var(--transition), transform var(--transition);
    position: relative;
    overflow: hidden;
}

.summary-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.summary-card.card-tomato::before {
    background: var(--tomato-red);
}

.summary-card.card-focus::before {
    background: #f39c12;
}

.summary-card.card-avg-duration::before {
    background: #9b59b6;
}

.summary-card.card-days::before {
    background: #3498db;
}

.summary-card.card-avg-tomato::before {
    background: var(--focus-teal);
}

.summary-card.card-avg-hours::before {
    background: #1abc9c;
}

.summary-card:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
}

.card-icon {
    font-size: 24px;
    margin-bottom: 6px;
}

.card-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.2;
    letter-spacing: -0.5px;
}

.card-label {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 4px;
    font-weight: 500;
}

.card-sub {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
}

/* ==================== 分区标题 ==================== */
.section-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 14px 0;
    padding-bottom: 10px;
    border-bottom: 2px solid var(--border-color);
}

/* ==================== 趋势对比区域 ==================== */
.trend-section {
    margin-bottom: 24px;
}

.trend-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
    gap: 14px;
}

.trend-card {
    background: var(--bg-card);
    border-radius: var(--radius-md);
    padding: 18px 20px;
    box-shadow: var(--shadow-sm);
    transition: box-shadow var(--transition);
}

.trend-card:hover {
    box-shadow: var(--shadow-md);
}

.trend-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
}

.trend-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}

.badge-week {
    background: #eef2ff;
    color: #4f6ef7;
}

.badge-3day {
    background: #fef3e2;
    color: #e67e22;
}

.trend-period {
    font-size: 13px;
    color: var(--text-secondary);
    font-weight: 500;
}

.trend-comparisons {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.trend-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 6px;
    padding: 8px 10px;
    background: var(--bg-page);
    border-radius: var(--radius-sm);
}

.trend-item-label {
    font-size: 13px;
    color: var(--text-secondary);
    font-weight: 500;
    min-width: 90px;
}

.trend-item-values {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}

.current-value {
    font-weight: 700;
    font-size: 15px;
    color: var(--text-primary);
}

.vs-separator {
    font-size: 11px;
    color: var(--text-muted);
    font-weight: 400;
}

.previous-value {
    font-weight: 500;
    font-size: 14px;
    color: var(--text-muted);
}

.change-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
    letter-spacing: 0.2px;
}

.change-positive {
    background: var(--green-bg);
    color: var(--green);
}

.change-negative {
    background: var(--red-bg);
    color: var(--red);
}

.change-neutral {
    background: var(--neutral-bg);
    color: var(--neutral);
}

/* ==================== 图表区域 ==================== */
.chart-section {
    margin-bottom: 10px;
}

.chart-wrapper {
    position: relative;
    width: 100%;
    height: 340px;
    background: var(--bg-card);
    border-radius: var(--radius-md);
    padding: 18px 14px 10px 10px;
    box-shadow: var(--shadow-sm);
    box-sizing: border-box;
}

.chart-wrapper canvas {
    width: 100% !important;
    height: 100% !important;
}

/* ==================== 波动性信息 ==================== */
.volatility-info {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
    padding: 10px 16px;
    background: var(--bg-card);
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow-sm);
    font-size: 13px;
}

.volatility-item {
    display: flex;
    align-items: center;
    gap: 4px;
}

.volatility-label {
    color: var(--text-muted);
    font-size: 12px;
}

.volatility-value {
    font-weight: 700;
    color: var(--text-primary);
    font-size: 14px;
}

.volatility-divider {
    color: var(--border-color);
    font-size: 14px;
}

.volatility-tip {
    color: var(--text-muted);
    font-size: 12px;
    font-style: italic;
    margin-left: auto;
}

/* ==================== 响应式适配 ==================== */
@media (max-width: 768px) {
    .tomato-trend-panel {
        padding: 16px 12px;
    }

    .summary-cards {
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 10px;
    }

    .summary-card {
        padding: 14px 10px;
    }

    .card-value {
        font-size: 22px;
    }

    .trend-cards {
        grid-template-columns: 1fr;
    }

    .chart-wrapper {
        height: 260px;
        padding: 10px 6px 6px 6px;
    }

    .panel-title {
        font-size: 18px;
    }

    .trend-item {
        flex-direction: column;
        align-items: flex-start;
    }

    .trend-item-label {
        min-width: auto;
    }

    .volatility-info {
        flex-direction: column;
        align-items: flex-start;
    }

    .volatility-tip {
        margin-left: 0;
    }
}

@media (max-width: 480px) {
    .summary-cards {
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
    }

    .card-value {
        font-size: 20px;
    }

    .card-icon {
        font-size: 20px;
    }

    .chart-wrapper {
        height: 220px;
    }

    .trend-item-values {
        gap: 4px;
    }

    .change-tag {
        font-size: 11px;
        padding: 1px 6px;
    }
}
</style>
