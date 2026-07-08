<template>
    <div class="app-container">
        <!-- 页面顶部：标题、状态徽章与重新设置按钮 -->
        <div class="page-header">
            <div class="page-title">
                <span class="icon">📊</span>
                体重趋势分析
            </div>
            <div class="header-actions">
                <span class="status-badge" :class="{ warning: statusWarning }">
                    <span class="status-dot"></span>
                    <span>{{ statusText }}</span>
                </span>
                <button class="reset-btn" @click="openSetupDialog">🔄 重新设置计划</button>
            </div>
        </div>

        <!-- 计划设置对话框 -->
        <div v-if="showSetupDialog" class="modal-overlay" @click.self="closeSetupDialog">
            <div class="modal-card">
                <h3 class="modal-title">{{ planExists ? '修改减重目标' : '设置减重计划' }}</h3>
                <div class="modal-body">
                    <label class="input-label">目标体重 (斤)</label>
                    <input v-model.number="targetWeightInput" type="number" step="0.1" min="30" max="200"
                        class="weight-input" placeholder="请输入目标体重" />
                </div>
                <div class="modal-footer">
                    <button class="btn btn-cancel" @click="closeSetupDialog">取消</button>
                    <button class="btn btn-confirm" @click="submitPlan">确认设置</button>
                </div>
            </div>
        </div>

        <!-- 图表卡片 -->
        <div class="chart-card">
            <div class="chart-card-header">
                <span class="chart-card-title">📈 体重变化趋势</span>
                <div class="chart-legend-inline">
                    <span class="legend-item">
                        <span class="legend-dot" style="background: #4a90d9"></span> 实际体重
                    </span>
                    <span class="legend-item">
                        <span class="legend-dash solid" style="border-color: #27ae60"></span> 推荐趋势
                    </span>
                    <span class="legend-item">
                        <span class="legend-dash" style="border-color: #e67e22"></span>
                        目标体重 ({{ planDetail?.target_weight ?? '--' }}斤)
                    </span>
                </div>
            </div>
            <div class="chart-scroll-wrapper" ref="chartScrollWrapper">
                <div class="chart-inner">
                    <canvas ref="chartCanvas"></canvas>
                </div>
            </div>
            <div class="scroll-hint" aria-hidden="true">
                <span class="scroll-hint-arrow">👈</span>
                左右滑动查看完整图表
                <span class="scroll-hint-arrow">👉</span>
            </div>
        </div>

        <!-- 统计卡片网格 -->
        <div class="stats-grid">
            <div class="stat-card highlight accent-blue">
                <span class="stat-icon-mini">⚖️</span>
                <span class="stat-label">当前体重</span>
                <span class="stat-value large">{{ stats.currentWeight }}</span>
                <span class="stat-sub neutral">{{ stats.currentWeightSub }}</span>
            </div>
            <div class="stat-card accent-teal">
                <span class="stat-icon-mini">🎯</span>
                <span class="stat-label">当前推荐体重</span>
                <span class="stat-value">{{ stats.recommendedWeight }}</span>
                <span class="stat-sub neutral">{{ stats.recommendedWeightSub }}</span>
            </div>
            <div class="stat-card accent-orange"
                :class="{ 'highlight-warn': stats.deviation > 0.3, highlight: stats.deviation < -0.3 }">
                <span class="stat-icon-mini">📐</span>
                <span class="stat-label">与推荐偏差</span>
                <span class="stat-value">{{ stats.deviationText }}</span>
                <span class="stat-sub" :class="stats.deviationClass">{{ stats.deviationSub }}</span>
            </div>
            <div class="stat-card">
                <span class="stat-icon-mini">🧮</span>
                <span class="stat-label">偏差变化量</span>
                <span class="stat-value">{{ stats.ddw }}</span>
                <span class="stat-sub" :class="stats.ddwClass">{{ stats.ddwSub }}</span>
            </div>
            <div class="stat-card accent-green">
                <span class="stat-icon-mini">🔽</span>
                <span class="stat-label">已减重量（累计）</span>
                <span class="stat-value">{{ stats.lostWeight }}</span>
                <span class="stat-sub positive">{{ stats.lostWeightSub }}</span>
            </div>
            <div class="stat-card accent-orange">
                <span class="stat-icon-mini">🎯</span>
                <span class="stat-label">还需减重（当前→目标）</span>
                <span class="stat-value">{{ stats.remainingWeight }}</span>
                <span class="stat-sub" :class="stats.remainingClass">{{ stats.remainingSub }}</span>
            </div>
            <div class="stat-card accent-teal">
                <span class="stat-icon-mini">📅</span>
                <span class="stat-label">计划已开始天数</span>
                <span class="stat-value">{{ stats.daysElapsed }}</span>
                <span class="stat-sub neutral">{{ stats.daysElapsedSub }}</span>
            </div>
            <div class="stat-card accent-purple">
                <span class="stat-icon-mini">⏳</span>
                <span class="stat-label">剩余天数</span>
                <span class="stat-value">{{ stats.daysRemaining }}</span>
                <span class="stat-sub neutral">{{ stats.daysRemainingSub }}</span>
            </div>
            <div class="stat-card">
                <span class="stat-icon-mini">📉</span>
                <span class="stat-label">最近7天体重变化</span>
                <span class="stat-value">{{ stats.weeklyChange }}</span>
                <span class="stat-sub" :class="stats.weeklyClass">{{ stats.weeklySub }}</span>
            </div>
            <div class="stat-card accent-purple">
                <span class="stat-icon-mini">🏁</span>
                <span class="stat-label">目标体重</span>
                <span class="stat-value">{{ stats.targetWeight }}</span>
                <span class="stat-sub neutral">计划结束时达成</span>
            </div>
            <div class="stat-card accent-green">
                <span class="stat-icon-mini">✅</span>
                <span class="stat-label">目标完成进度</span>
                <span class="stat-value">{{ stats.progressPercent }}</span>
                <div class="progress-wrap">
                    <div class="progress-bar-outer">
                        <div class="progress-bar-inner" :style="{ width: stats.progressBarWidth }"></div>
                    </div>
                    <div class="progress-label">{{ stats.progressLabel }}</div>
                </div>
            </div>
            <div class="stat-card">
                <span class="stat-icon-mini">📊</span>
                <span class="stat-label">累计偏离值（实际vs推荐）</span>
                <span class="stat-value">{{ stats.cumulativeDeviation }}</span>
                <span class="stat-sub neutral">{{ stats.cumulativeSub }}</span>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import axios from 'axios'
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)

// ---------- 类型定义 ----------
interface PlanDetailResponse {
    target_weight: number
    delta_weight: number
    target_line: Record<string, number>
    user_line: Record<string, number>
}

interface StatsData {
    currentWeight: string
    currentWeightSub: string
    recommendedWeight: string
    recommendedWeightSub: string
    deviationText: string
    deviationSub: string
    deviationClass: string
    deviation: number
    targetWeight: string
    lostWeight: string
    lostWeightSub: string
    remainingWeight: string
    remainingSub: string
    remainingClass: string
    daysElapsed: string
    daysElapsedSub: string
    daysRemaining: string
    daysRemainingSub: string
    weeklyChange: string
    weeklySub: string
    weeklyClass: string
    ddw: string
    ddwSub: string
    ddwClass: string
    progressPercent: string
    progressBarWidth: string
    progressLabel: string
    cumulativeDeviation: string
    cumulativeSub: string
}

// ---------- 响应式状态 ----------
const planExists = ref<boolean | null>(null)
const showSetupDialog = ref(false)
const targetWeightInput = ref<number>(70)
const planDetail = ref<PlanDetailResponse | null>(null)
const loading = ref(false)

const chartCanvas = ref<HTMLCanvasElement | null>(null)
const chartScrollWrapper = ref<HTMLDivElement | null>(null)
let chartInstance: Chart | null = null

const statusText = ref('加载中...')
const statusWarning = ref(false)

const stats = reactive<StatsData>({
    currentWeight: '--',
    currentWeightSub: '--',
    recommendedWeight: '--',
    recommendedWeightSub: '--',
    deviationText: '--',
    deviationSub: '--',
    deviationClass: 'neutral',
    deviation: 0,
    targetWeight: '--',
    lostWeight: '--',
    lostWeightSub: '--',
    remainingWeight: '--',
    remainingSub: '--',
    remainingClass: 'neutral',
    daysElapsed: '--',
    daysElapsedSub: '--',
    daysRemaining: '--',
    daysRemainingSub: '--',
    weeklyChange: '--',
    weeklySub: '--',
    weeklyClass: 'neutral',
    ddw: '--',
    ddwSub: '--',
    ddwClass: 'neutral',
    progressPercent: '--',
    progressBarWidth: '0%',
    progressLabel: '--',
    cumulativeDeviation: '--',
    cumulativeSub: '--'
})

// ---------- 工具函数 ----------
function parseDate(str: string): Date {
    return new Date(str.replace(/-/g, '/'))
}

function formatDate(date: Date): string {
    return `${date.getMonth() + 1}/${date.getDate()}`
}

function daysBetween(d1: Date, d2: Date): number {
    return Math.round((d2.getTime() - d1.getTime()) / 86400000)
}

// ---------- 数据获取与处理 ----------
async function checkPlanInit() {
    try {
        const { data } = await axios.get<boolean>('/weight/plan/init')
        planExists.value = data
        if (!data) {
            showSetupDialog.value = true
        }
    } catch (error) {
        console.error('检查计划状态失败', error)
    }
}

async function fetchPlanDetail() {
    loading.value = true
    try {
        const { data } = await axios.get<PlanDetailResponse>('/weight/plan/detail')
        planDetail.value = data
        processStats(data)
        await nextTick()
        renderChart(data)
    } catch (error) {
        console.error('获取计划详情失败', error)
        statusText.value = '数据加载失败'
        statusWarning.value = true
    } finally {
        loading.value = false
    }
}

function processStats(detail: PlanDetailResponse) {
    const targetLine = detail.target_line
    const userLine = detail.user_line

    // 提取日期并排序
    const targetDates = Object.keys(targetLine).sort()
    const userDates = Object.keys(userLine).sort()

    if (targetDates.length === 0) {
        statusText.value = '无计划数据'
        return
    }

    const startDate = parseDate(targetDates[0])
    const endDate = parseDate(targetDates[targetDates.length - 1])
    const startWeight = targetLine[targetDates[0]]
    const targetWeight = detail.target_weight

    const lastUserDateStr = userDates.length > 0 ? userDates[userDates.length - 1] : targetDates[0]
    const yestodayDateStr = userDates.length > 1 ? userDates[userDates.length - 2] : targetDates[0]
    const currentDate = parseDate(lastUserDateStr)
    const currentWeight = userLine[lastUserDateStr] ?? startWeight
    const recommendedWeight = targetLine[lastUserDateStr] ?? targetWeight

    // 天数
    const elapsedDays = daysBetween(startDate, currentDate) + 1
    const remainingDays = daysBetween(currentDate, endDate)

    // 体重变化
    const deviation = currentWeight - recommendedWeight
    const lostWeight = startWeight - currentWeight
    const remainingWeight = currentWeight - targetWeight
    const progressPercent = startWeight !== targetWeight ? (lostWeight / (startWeight - targetWeight)) * 100 : 0

    // 体重与目标值的二阶偏差
    const yestodayUW = userLine[yestodayDateStr] ?? startWeight
    const yestodayRW = targetLine[yestodayDateStr] ?? targetWeight
    const ddw = deviation - (yestodayUW - yestodayRW)

    // 最近7天变化
    let weeklyChange = 0
    if (userDates.length >= 2) {
        const recentDates = userDates.slice(-7)
        const firstRecent = userLine[recentDates[0]]
        const lastRecent = userLine[recentDates[recentDates.length - 1]]
        weeklyChange = lastRecent - firstRecent
    }

    // 更新stats
    stats.currentWeight = currentWeight.toFixed(2) + ' 斤'
    stats.currentWeightSub = `起始 ${startWeight.toFixed(1)}斤 · 目标 ${targetWeight.toFixed(1)}斤`
    stats.recommendedWeight = recommendedWeight.toFixed(2) + ' 斤'
    stats.recommendedWeightSub = `第${elapsedDays}天推荐值`
    stats.deviation = deviation
    stats.deviationText = (deviation >= 0 ? '+' : '') + deviation.toFixed(2) + ' 斤'
    if (Math.abs(deviation) < 0.3) {
        stats.deviationSub = '接近推荐值 ✓'
        stats.deviationClass = 'positive'
    } else if (deviation > 0) {
        stats.deviationSub = '高于推荐值，需关注'
        stats.deviationClass = 'negative'
    } else {
        stats.deviationSub = '低于推荐值，表现优秀'
        stats.deviationClass = 'positive'
    }
    stats.targetWeight = targetWeight.toFixed(1) + ' 斤'
    stats.lostWeight = (lostWeight >= 0 ? '-' : '+') + Math.abs(lostWeight).toFixed(2) + ' 斤'
    stats.lostWeightSub = `完成进度 ${progressPercent.toFixed(1)}%`
    stats.remainingWeight = remainingWeight.toFixed(2) + ' 斤'
    if (remainingWeight <= 0) {
        stats.remainingSub = '🎉 已达成目标！'
        stats.remainingClass = 'positive'
    } else if (remainingWeight <= 3) {
        stats.remainingSub = '接近目标，继续加油'
        stats.remainingClass = 'positive'
    } else {
        stats.remainingSub = '距离目标还需努力'
        stats.remainingClass = 'neutral'
    }
    stats.daysElapsed = elapsedDays + ' 天'
    stats.daysElapsedSub = `自 ${formatDate(startDate)} 开始`
    stats.daysRemaining = Math.max(0, remainingDays) + ' 天'
    stats.daysRemainingSub =
        remainingDays > 0
            ? `预计 ${formatDate(endDate)} 结束`
            : '计划已到期'

    stats.weeklyChange = (weeklyChange >= 0 ? '+' : '') + weeklyChange.toFixed(2) + ' 斤'
    if (weeklyChange < -0.3) {
        stats.weeklySub = '↓ 下降趋势良好'
        stats.weeklyClass = 'positive'
    } else if (weeklyChange > 0.3) {
        stats.weeklySub = '↑ 有所反弹，注意控制'
        stats.weeklyClass = 'negative'
    } else {
        stats.weeklySub = '→ 基本持平'
        stats.weeklyClass = 'neutral'
    }

    stats.ddw = ddw.toFixed(1) + '斤'
    if (ddw > 0.2) {
        stats.ddwSub = '↓ 与目标差距在增大'
        stats.ddwClass = 'negative'
    } else if (ddw < -0.2) {
        stats.ddwSub = '↑ 与目标差距在缩下'
        stats.ddwClass = 'positive'
    } else {
        stats.ddwSub = '→ 与目标差距持平'
        stats.ddwClass = 'neutral'
    }

    stats.progressPercent = progressPercent.toFixed(1) + '%'
    stats.progressBarWidth = Math.min(100, progressPercent) + '%'
    stats.progressLabel = `已减 ${lostWeight.toFixed(2)} / ${(startWeight - targetWeight).toFixed(1)} 斤`

    stats.cumulativeDeviation = (detail.delta_weight >= 0 ? '+' : '') + detail.delta_weight.toFixed(2) + ' 斤·天'
    if (detail.delta_weight > 5) {
        stats.cumulativeSub = '整体高于推荐线，需加强'
    } else if (detail.delta_weight < -5) {
        stats.cumulativeSub = '整体低于推荐线，表现出色'
    } else {
        stats.cumulativeSub = '整体接近推荐轨迹'
    }

    // 更新顶部状态
    if (remainingWeight <= 0) {
        statusText.value = '🎉 目标已达成'
        statusWarning.value = false
    } else if (deviation > 1.0) {
        statusText.value = '⚠️ 略高于推荐，需关注'
        statusWarning.value = true
    } else if (Math.abs(deviation) < 0.8) {
        statusText.value = '进展顺利，按计划进行'
        statusWarning.value = false
    } else {
        statusText.value = '计划进行中'
        statusWarning.value = false
    }
}

// ---------- 图表渲染 ----------
function renderChart(detail: PlanDetailResponse) {
    if (!chartCanvas.value) return

    const targetLine = detail.target_line
    const userLine = detail.user_line
    const targetDates = Object.keys(targetLine).sort()
    const userDates = Object.keys(userLine).sort()

    const labels = targetDates.map((d) => {
        const date = parseDate(d)
        return formatDate(date)
    })

    const actualData = targetDates.map((date) => {
        // 如果 userLine 中有该日期的数据则返回，否则返回 null
        return userLine[date] !== undefined ? userLine[date] : null
    })
    const recommendedData = targetDates.map((date) => targetLine[date])
    const targetWeight = detail.target_weight
    const targetLineData = new Array(targetDates.length).fill(targetWeight)

    // 找到最后一个有实际数据的索引，用于标记“当前”
    const lastUserDate = userDates.length > 0 ? userDates[userDates.length - 1] : targetDates[0]
    const currentIndex = targetDates.indexOf(lastUserDate)

    // 销毁旧图表
    if (chartInstance) {
        chartInstance.destroy()
        chartInstance = null
    }

    const ctx = chartCanvas.value.getContext('2d')
    if (!ctx) return

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: '实际体重',
                    data: actualData,
                    borderColor: '#4a90d9',
                    backgroundColor: 'rgba(74,144,217,0.08)',
                    borderWidth: 2.5,
                    pointRadius: (ctx: any) => {
                        const idx = ctx.dataIndex
                        if (idx === currentIndex) return 6
                        if (idx > currentIndex) return 0
                        return idx % 7 === 0 || idx === 0 ? 3.5 : 1.5
                    },
                    pointBackgroundColor: (ctx: any) => (ctx.dataIndex === currentIndex ? '#e74c3c' : '#4a90d9'),
                    pointBorderColor: (ctx: any) => (ctx.dataIndex === currentIndex ? '#fff' : '#4a90d9'),
                    pointBorderWidth: (ctx: any) => (ctx.dataIndex === currentIndex ? 3 : 1),
                    pointHoverRadius: 7,
                    tension: 0.35,
                    fill: true,
                    spanGaps: false,
                    order: 1
                },
                {
                    label: '推荐体重趋势',
                    data: recommendedData,
                    borderColor: '#27ae60',
                    borderWidth: 2.5,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    tension: 0,
                    fill: false,
                    spanGaps: true,
                    order: 2
                },
                {
                    label: `目标体重 (${targetWeight}斤)`,
                    data: targetLineData,
                    borderColor: '#e67e22',
                    borderWidth: 1.8,
                    borderDash: [8, 5],
                    pointRadius: 0,
                    tension: 0,
                    fill: false,
                    spanGaps: true,
                    order: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.2,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(30,32,38,0.94)',
                    titleFont: { size: 13, weight: 600 },
                    bodyFont: { size: 12 },
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        title: (ctx) => {
                            const idx = ctx[0].dataIndex
                            const dateStr = labels[idx]
                            const fullDate = parseDate(targetDates[idx])
                            const wd = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][fullDate.getDay()]
                            let suffix = ''
                            if (idx === currentIndex) suffix = ' 【当前】'
                            else if (idx > currentIndex) suffix = '（未来预测）'
                            return dateStr + ' ' + wd + suffix
                        },
                        label: (ctx) => {
                            if (ctx.dataset.label?.startsWith('目标体重')) return `目标体重: ${targetWeight.toFixed(1)} 斤`
                            if (ctx.parsed.y === null) return ctx.dataset.label + ': 暂无数据'
                            return ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(2) + ' 斤'
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: '日期 (月/日)', font: { size: 12, weight: 600 }, color: '#5f6368' },
                    ticks: { maxTicksLimit: 14, font: { size: 10.5 }, color: '#6b7280' },
                    grid: { color: 'rgba(0,0,0,0.04)' },
                    border: { color: '#d0d3d8' }
                },
                y: {
                    title: { display: true, text: '体重 (斤)', font: { size: 12, weight: 600 }, color: '#5f6368' },
                    min: Math.floor(targetWeight - 3),
                    max: Math.ceil(startWeightFromDetail(detail) + 3),
                    ticks: { stepSize: 1, font: { size: 10.5 }, color: '#6b7280', callback: (v) => (v as number).toFixed(1) + ' 斤' },
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    border: { color: '#d0d3d8' }
                }
            }
        },
        plugins: [
            {
                id: 'currentLinePlugin',
                afterDraw(chart: Chart) {
                    const xScale = chart.scales.x
                    // const yScale = chart.scales.y
                    const ctx2 = chart.ctx
                    const area = chart.chartArea
                    if (currentIndex < 0 || currentIndex >= labels.length) return
                    const xPos = xScale.getPixelForValue(currentIndex)
                    if (xPos < area.left || xPos > area.right) return
                    ctx2.save()
                    ctx2.beginPath()
                    ctx2.setLineDash([4, 4])
                    ctx2.strokeStyle = 'rgba(100,100,110,0.55)'
                    ctx2.lineWidth = 1.5
                    ctx2.moveTo(xPos, area.top)
                    ctx2.lineTo(xPos, area.bottom)
                    ctx2.stroke()
                    ctx2.setLineDash([])
                    ctx2.fillStyle = 'rgba(100,100,110,0.9)'
                    ctx2.font = '600 11px -apple-system, "PingFang SC", sans-serif'
                    ctx2.textAlign = 'center'
                    // ctx2.fillText('当前', xPos, area.top+12)
                    ctx2.beginPath()
                    ctx2.arc(xPos, area.top - 2, 4, 0, Math.PI * 2)
                    ctx2.fillStyle = 'rgba(100,100,110,0.7)'
                    ctx2.fill()
                    ctx2.restore()
                }
            }
        ]
    })

    // 滚动到当前数据点
    setTimeout(() => {
        if (chartScrollWrapper.value) {
            const wrapper = chartScrollWrapper.value
            const inner = wrapper.querySelector('.chart-inner') as HTMLElement
            if (inner && inner.scrollWidth > wrapper.clientWidth) {
                const ratio = currentIndex / (labels.length - 1)
                const targetScroll = ratio * inner.scrollWidth - wrapper.clientWidth * 0.4
                wrapper.scrollLeft = Math.min(targetScroll, inner.scrollWidth - wrapper.clientWidth)
            }
        }
    }, 300)
}

function startWeightFromDetail(detail: PlanDetailResponse): number {
    const dates = Object.keys(detail.target_line).sort()
    return detail.target_line[dates[0]]
}

// ---------- 计划设置/重置 ----------
function openSetupDialog() {
    // 如果已有计划，可预填当前目标体重
    if (planDetail.value) {
        targetWeightInput.value = planDetail.value.target_weight
    } else {
        targetWeightInput.value = 110
    }
    showSetupDialog.value = true
}

function closeSetupDialog() {
    showSetupDialog.value = false
}

async function submitPlan() {
    if (!targetWeightInput.value || targetWeightInput.value <= 0) {
        alert('请输入有效的目标体重')
        return
    }
    try {
        const { data } = await axios.post<boolean>('/weight/plan/init', {
            target_weight: targetWeightInput.value
        })
        if (data) {
            showSetupDialog.value = false
            planExists.value = true
            await fetchPlanDetail()
        } else {
            alert('设置失败，请重试')
        }
    } catch (error) {
        console.error('提交计划失败', error)
        alert('网络错误，设置失败')
    }
}

// ---------- 生命周期 ----------
onMounted(async () => {
    await checkPlanInit()
    if (planExists.value) {
        await fetchPlanDetail()
    }
})
</script>

<style scoped>
/* 保留原有的所有样式，略作微调以适应 Vue */
.app-container {
    --bg: #f5f6f8;
    --card-bg: #ffffff;
    --text-primary: #1a1d23;
    --text-secondary: #5f6368;
    --text-muted: #8a8f96;
    --border: #e8eaed;
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.06);
    --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.06), 0 4px 16px rgba(0, 0, 0, 0.04);
    --shadow-lg: 0 4px 16px rgba(0, 0, 0, 0.08), 0 8px 32px rgba(0, 0, 0, 0.04);
    --blue: #4a90d9;
    --blue-dark: #357abd;
    --blue-light: #e8f1fb;
    --green: #27ae60;
    --green-dark: #1e8a4c;
    --green-light: #eaf7ef;
    --orange: #e67e22;
    --orange-light: #fef5ed;
    --red: #e74c3c;
    --red-light: #fdedec;
    --purple: #8e44ad;
    --purple-light: #f5eef8;
    --teal: #17a2b8;
    --teal-light: #eaf7f9;
    --radius-sm: 10px;
    --radius: 14px;
    --radius-lg: 18px;
    --transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

.app-container {
    max-width: 1100px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 18px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei',
        'Noto Sans SC', sans-serif;
    background: var(--bg);
    min-height: 100vh;
    padding: 16px;
    color: var(--text-primary);
}

.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
}

.page-title {
    font-size: 1.6rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 10px;
}

.page-title .icon {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: linear-gradient(135deg, #4a90d9, #27ae60);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    background: var(--green-light);
    color: var(--green-dark);
}

.status-badge.warning {
    background: var(--orange-light);
    color: #c26a1a;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {

    0%,
    100% {
        opacity: 1;
    }

    50% {
        opacity: 0.4;
    }
}

.reset-btn {
    background: #ffffff;
    border: 1px solid var(--border);
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    transition: var(--transition);
    display: flex;
    align-items: center;
    gap: 4px;
}

.reset-btn:hover {
    background: var(--bg);
    border-color: var(--blue);
}

/* 模态框 */
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal-card {
    background: white;
    border-radius: var(--radius-lg);
    padding: 24px;
    width: 90%;
    max-width: 400px;
    box-shadow: var(--shadow-lg);
}

.modal-title {
    font-size: 1.2rem;
    margin-bottom: 20px;
    font-weight: 650;
}

.input-label {
    display: block;
    margin-bottom: 8px;
    font-size: 0.9rem;
    color: var(--text-secondary);
}

.weight-input {
    width: 100%;
    padding: 10px 14px;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 1rem;
    outline: none;
}

.modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;
}

.btn {
    padding: 8px 18px;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-weight: 500;
}

.btn-cancel {
    background: #f0f0f0;
    color: #333;
}

.btn-confirm {
    background: var(--blue);
    color: white;
}

/* 其余卡片与图表样式保持完全一致，省略重复代码，实际文件中需完整包含 */
.chart-card {
    background: var(--card-bg);
    border-radius: var(--radius-lg);
    padding: 20px 16px 14px;
    box-shadow: var(--shadow-md);
    border: 1px solid var(--border);
}

.chart-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    margin-bottom: 10px;
}

.chart-card-title {
    font-size: 1rem;
    font-weight: 650;
}

.chart-legend-inline {
    display: flex;
    gap: 16px;
    font-size: 0.8rem;
    color: var(--text-secondary);
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
}

.legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
}

.legend-dash {
    width: 16px;
    height: 2px;
    border-top: 2px dashed;
}

.legend-dash.solid {
    border-top-style: solid;
}

.chart-scroll-wrapper {
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: thin;
    scrollbar-color: #c4c8ce transparent;
}

.chart-scroll-wrapper::-webkit-scrollbar {
    height: 5px;
}

.chart-scroll-wrapper::-webkit-scrollbar-thumb {
    background: #c4c8ce;
    border-radius: 10px;
}

.chart-inner {
    min-width: 650px;
    width: 100%;
}

.scroll-hint {
    display: none;
    text-align: center;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 8px;
}

@media (max-width: 899px) {
    .scroll-hint {
        display: flex;
        justify-content: center;
        gap: 6px;
    }
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}

@media (max-width: 1024px) {
    .stats-grid {
        grid-template-columns: repeat(3, 1fr);
    }
}

@media (max-width: 640px) {
    .stats-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

.stat-card {
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 14px 16px;
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 4px;
    position: relative;
}

.stat-card.highlight {
    border-left: 3px solid var(--blue);
}

.stat-card.accent-blue {
    border-left: 3px solid var(--blue);
}

.stat-card.accent-green {
    border-left: 3px solid var(--green);
}

.stat-card.accent-orange {
    border-left: 3px solid var(--orange);
}

.stat-card.accent-purple {
    border-left: 3px solid var(--purple);
}

.stat-card.accent-teal {
    border-left: 3px solid var(--teal);
}

.stat-label {
    font-size: 0.78rem;
    color: var(--text-muted);
    text-transform: uppercase;
}

.stat-value {
    font-size: 1.55rem;
    font-weight: 700;
}

.stat-value.large {
    font-size: 2rem;
}

.stat-sub {
    font-size: 0.75rem;
}

.stat-sub.positive {
    color: var(--green-dark);
}

.stat-sub.negative {
    color: var(--red);
}

.stat-sub.neutral {
    color: var(--text-muted);
}

.stat-icon-mini {
    position: absolute;
    top: 10px;
    right: 12px;
    font-size: 1.4rem;
    opacity: 0.25;
}

.progress-wrap {
    margin-top: 2px;
}

.progress-bar-outer {
    height: 7px;
    background: #e9ecef;
    border-radius: 10px;
    overflow: hidden;
}

.progress-bar-inner {
    height: 100%;
    border-radius: 10px;
    background: linear-gradient(90deg, #4a90d9, #27ae60);
}

.progress-label {
    font-size: 0.72rem;
    color: var(--text-muted);
    text-align: right;
}
</style>