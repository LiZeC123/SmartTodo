<template>
  <div class="rowing-page">
    <div class="rowing-container">
      <!-- 顶部统计信息栏 -->
      <header class="stats-header">
        <div class="stat-card">
          <div class="stat-label">运动时长</div>
          <div class="stat-value">{{ formattedTime }}</div>
          <div class="stat-unit">分钟:秒</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">阻力档位</div>
          <div class="stat-value resistance-value">
            <span class="value-num">{{ resistance }}</span>
          </div>
          <div class="stat-unit">档位 1-31</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">划桨频率</div>
          <div class="stat-value frequency-value">
            <span class="value-num">{{ frequency }}</span>
          </div>
          <div class="stat-unit">次/分钟</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">拉桨次数</div>
          <div class="stat-value">{{ strokeCount }}</div>
          <div class="stat-unit">次</div>
        </div>
        <div v-if="planData && planData.resistance.length > 0" class="stat-card plan-progress">
          <div class="stat-label">计划进度</div>
          <div class="stat-value">{{ currentPlanMinute + 1 }} / {{ planData.resistance.length }}</div>
          <div class="stat-unit">分钟</div>
        </div>
      </header>

      <!-- 中部动画区域 -->
      <section class="animation-area">
        <!-- 呼吸圆形 -->
        <div class="breath-circle-wrapper">
          <div class="breath-circle-container">
            <div
              class="breath-circle"
              :style="breathCircleStyle"
            >
              <div class="circle-inner"></div>
              <div class="circle-glow"></div>
            </div>
            <div class="circle-ring ring-1" :style="ringStyle1"></div>
            <div class="circle-ring ring-2" :style="ringStyle2"></div>
          </div>
        </div>

        <!-- 滑动滑块 -->
        <div class="slider-track-wrapper">
          <div class="slider-track">
            <div class="track-line"></div>
            <div class="track-mark track-mark-left"></div>
            <div class="track-mark track-mark-right"></div>
            <div
              class="slider-thumb"
              :style="sliderThumbStyle"
            >
              <div class="thumb-inner"></div>
            </div>
            <div class="track-end track-end-left">
              <div class="end-dot"></div>
            </div>
            <div class="track-end track-end-right">
              <div class="end-dot"></div>
            </div>
          </div>
        </div>
      </section>

      <!-- 底部完成提示（仅在计划完成后显示） -->
      <footer class="controls-area" v-if="planComplete">
        <div class="complete-banner">
          <span class="complete-icon">🎉</span>
          <span>运动计划已完成，数据已自动提交</span>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import axios from 'axios'

// ============ 类型定义 ============
interface PlanData {
  resistance: number[]
  frequency: number[]
}

interface ExerciseRecord {
  type: string
  time: number
  extra: {
    stroke_count: number
  }
}

// ============ 常量 ============
const DRIVE_RATIO = 0.35
const RECOVERY_RATIO = 1 - DRIVE_RATIO
const MIN_SCALE = 0.55
const MAX_SCALE = 1.0
const SLIDER_MIN_PERCENT = 8
const SLIDER_MAX_PERCENT = 92
const DEFAULT_RESISTANCE = 10
const DEFAULT_FREQUENCY = 20
const DEFAULT_PLAN_DURATION_MINUTES = 30 // 无计划时的默认时长

// ============ 响应式状态 ============
const elapsedTime = ref(0)
const resistance = ref(DEFAULT_RESISTANCE)
const frequency = ref(DEFAULT_FREQUENCY)
const strokeCount = ref(0)
const planData = ref<PlanData | null>(null)
const planComplete = ref(false)

// 动画相关
const accumulatedProgress = ref(0)
const animationFrameId = ref<number | null>(null)
const lastFrameTime = ref<number | null>(null)
const timerIntervalId = ref<number | null>(null)
let autoSubmitted = false // 防止重复提交

// ============ 计算属性 ============
const currentPlanMinute = computed(() => {
  if (!planData.value || planData.value.resistance.length === 0) return 0
  return Math.min(Math.floor(elapsedTime.value / 60), planData.value.resistance.length - 1)
})

const formattedTime = computed(() => {
  const minutes = Math.floor(elapsedTime.value / 60)
  const seconds = elapsedTime.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const cycleProgress = computed(() => {
  return accumulatedProgress.value % 1
})

const breathCircleStyle = computed(() => {
  const progress = cycleProgress.value
  let scale: number

  if (progress < DRIVE_RATIO) {
    const norm = progress / DRIVE_RATIO
    const eased = easeInOutSine(norm)
    scale = MAX_SCALE - (MAX_SCALE - MIN_SCALE) * eased
  } else {
    const norm = (progress - DRIVE_RATIO) / RECOVERY_RATIO
    const eased = easeInOutSine(norm)
    scale = MIN_SCALE + (MAX_SCALE - MIN_SCALE) * eased
  }

  return {
    transform: `scale(${scale})`,
    transition: 'none',
  }
})

const ringStyle1 = computed(() => {
  const progress = cycleProgress.value
  let scale: number

  if (progress < DRIVE_RATIO) {
    const norm = progress / DRIVE_RATIO
    const eased = easeInOutSine(norm)
    scale = MAX_SCALE - 0.15 - (MAX_SCALE - MIN_SCALE - 0.1) * eased
  } else {
    const norm = (progress - DRIVE_RATIO) / RECOVERY_RATIO
    const eased = easeInOutSine(norm)
    scale = MIN_SCALE + 0.05 + (MAX_SCALE - MIN_SCALE - 0.15) * eased
  }

  return {
    transform: `scale(${scale})`,
    opacity: 0.35 + 0.2 * (1 - Math.abs(scale - (MAX_SCALE + MIN_SCALE) / 2) / ((MAX_SCALE - MIN_SCALE) / 2)),
    transition: 'none',
  }
})

const ringStyle2 = computed(() => {
  const progress = cycleProgress.value
  let scale: number

  if (progress < DRIVE_RATIO) {
    const norm = progress / DRIVE_RATIO
    const eased = easeInOutSine(norm)
    scale = MAX_SCALE - 0.3 - (MAX_SCALE - MIN_SCALE - 0.25) * eased
  } else {
    const norm = (progress - DRIVE_RATIO) / RECOVERY_RATIO
    const eased = easeInOutSine(norm)
    scale = MIN_SCALE + 0.15 + (MAX_SCALE - MIN_SCALE - 0.3) * eased
  }

  return {
    transform: `scale(${scale})`,
    opacity: 0.2 + 0.15 * (1 - Math.abs(scale - (MAX_SCALE + MIN_SCALE) / 2) / ((MAX_SCALE - MIN_SCALE) / 2)),
    transition: 'none',
  }
})

const sliderThumbStyle = computed(() => {
  const progress = cycleProgress.value
  let positionPercent: number

  if (progress < DRIVE_RATIO) {
    const norm = progress / DRIVE_RATIO
    const eased = easeInOutSine(norm)
    positionPercent = SLIDER_MIN_PERCENT + (SLIDER_MAX_PERCENT - SLIDER_MIN_PERCENT) * eased
  } else {
    const norm = (progress - DRIVE_RATIO) / RECOVERY_RATIO
    const eased = easeInOutSine(norm)
    positionPercent = SLIDER_MAX_PERCENT - (SLIDER_MAX_PERCENT - SLIDER_MIN_PERCENT) * eased
  }

  return {
    left: `${positionPercent}%`,
    transition: 'none',
  }
})

// ============ 方法 ============

function easeInOutSine(t: number): number {
  return (1 - Math.cos(Math.PI * t)) / 2
}

function animateLoop(timestamp: number) {
  if (lastFrameTime.value === null) {
    lastFrameTime.value = timestamp
    animationFrameId.value = requestAnimationFrame(animateLoop)
    return
  }

  const deltaTime = (timestamp - lastFrameTime.value) / 1000
  lastFrameTime.value = timestamp

  const clampedDelta = Math.min(deltaTime, 0.1)

  if (clampedDelta > 0) {
    const periodSeconds = 60 / frequency.value
    const progressIncrement = clampedDelta / periodSeconds
    accumulatedProgress.value += progressIncrement

    const newStrokeCount = Math.floor(accumulatedProgress.value)
    if (newStrokeCount > strokeCount.value) {
      strokeCount.value = newStrokeCount
    }
  }

  animationFrameId.value = requestAnimationFrame(animateLoop)
}

function startAnimation() {
  if (animationFrameId.value !== null) return
  lastFrameTime.value = null
  animationFrameId.value = requestAnimationFrame(animateLoop)
}

function stopAnimation() {
  if (animationFrameId.value !== null) {
    cancelAnimationFrame(animationFrameId.value)
    animationFrameId.value = null
  }
  lastFrameTime.value = null
}

function startTimer() {
  if (timerIntervalId.value !== null) return
  timerIntervalId.value = window.setInterval(() => {
    elapsedTime.value += 1
    checkPlanProgress()
  }, 1000)
}

function stopTimer() {
  if (timerIntervalId.value !== null) {
    clearInterval(timerIntervalId.value)
    timerIntervalId.value = null
  }
}

function checkPlanProgress() {
  if (!planData.value || planData.value.resistance.length === 0) {
    // 无计划时持续运行，不自动结束
    return
  }
  if (planComplete.value) return

  const totalPlanSeconds = planData.value.resistance.length * 60
  if (elapsedTime.value >= totalPlanSeconds) {
    planComplete.value = true
    // 保持最后的阻力和频率
    const lastIndex = planData.value.resistance.length - 1
    resistance.value = planData.value.resistance[lastIndex]
    frequency.value = planData.value.frequency[lastIndex]
    // 自动提交数据
    if (!autoSubmitted) {
      autoSubmitted = true
      submitExerciseRecord(elapsedTime.value, strokeCount.value)
    }
    stopTimer()
    return
  }

  // 根据当前时间更新阻力和频率
  const minuteIndex = Math.floor(elapsedTime.value / 60)
  if (minuteIndex < planData.value.resistance.length) {
    resistance.value = planData.value.resistance[minuteIndex]
    frequency.value = planData.value.frequency[minuteIndex]
  }
}

async function submitExerciseRecord(time: number, strokes: number) {
  try {
    const record: ExerciseRecord = {
      type: 'RowingMachine',
      time: time,
      extra: {
        stroke_count: strokes,
      },
    }
    await axios.post('exercise/record', record)
    console.log('运动记录已提交:', record)
  } catch (error) {
    console.error('提交运动记录失败:', error)
  }
}

function buildDefaultPlan(): PlanData {
  const res: PlanData = {
    resistance: new Array(DEFAULT_PLAN_DURATION_MINUTES).fill(DEFAULT_RESISTANCE),
    frequency: new Array(DEFAULT_PLAN_DURATION_MINUTES).fill(DEFAULT_FREQUENCY),
  }
  return res
}

async function fetchPlanAndStart() {
  try {
    const response = await axios.get<PlanData>('exercise/plan/rowing')
    if (response.data && response.data.resistance && response.data.frequency && response.data.resistance.length > 0) {
      planData.value = response.data
    } else {
      // 数据无效，使用默认计划
      planData.value = buildDefaultPlan()
    }
  } catch (error) {
    console.error('获取运动计划失败，使用默认计划:', error)
    planData.value = buildDefaultPlan()
  }

  // 设置初始值
  if (planData.value && planData.value.resistance.length > 0) {
    resistance.value = planData.value.resistance[0]
    frequency.value = planData.value.frequency[0]
  }

  // 启动计时与动画
  startTimer()
}

// 生命周期
onMounted(() => {
  startAnimation()
  fetchPlanAndStart()
})

onUnmounted(() => {
  stopAnimation()
  stopTimer()
})
</script>

<style scoped>
/* ============ 全局页面样式 ============ */
.rowing-page {
  --bg-primary: #f8fafc;
  --bg-card: #ffffff;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --text-muted: #94a3b8;
  --accent: #0ea5e9;
  --accent-light: #e0f2fe;
  --accent-dark: #0284c7;
  --breath-inner: #38bdf8;
  --breath-outer: #7dd3fc;
  --breath-glow: #bae6fd;
  --slider-track: #e2e8f0;
  --slider-thumb: #0ea5e9;
  --slider-thumb-glow: #38bdf8;
  --btn-start-bg: #0ea5e9;
  --btn-start-hover: #0284c7;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
  --shadow-lg: 0 10px 25px -3px rgba(0, 0, 0, 0.08), 0 4px 10px -4px rgba(0, 0, 0, 0.05);
  --shadow-glow: 0 0 30px rgba(14, 165, 233, 0.25);
  --radius-sm: 8px;
  --radius-md: 14px;
  --radius-lg: 20px;
  --radius-xl: 28px;
  --radius-full: 50%;

  width: 100%;
  min-height: 100vh;
  min-height: 100dvh;
  background: linear-gradient(160deg, #f0f7ff 0%, #f8fafc 30%, #f1f5f9 70%, #e8f4fd 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow-x: hidden;
  -webkit-tap-highlight-color: transparent;
}

.rowing-container {
  width: 100%;
  max-width: 900px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-sizing: border-box;
}

/* ============ 顶部统计信息栏 ============ */
.stats-header {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}

.stat-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  text-align: center;
  box-shadow: var(--shadow-sm);
  flex: 1 1 auto;
  min-width: 80px;
  max-width: 140px;
  border: 1px solid #f1f5f9;
  transition: box-shadow 0.3s ease;
}

.stat-card:hover {
  box-shadow: var(--shadow-md);
}

.stat-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-unit {
  font-size: 0.65rem;
  color: var(--text-muted);
  margin-top: 2px;
}

.resistance-value,
.frequency-value {
  display: flex;
  align-items: center;
  justify-content: center;
}

.value-num {
  min-width: 32px;
  text-align: center;
  font-size: 1.5rem;
  font-weight: 700;
}

.plan-progress {
  border-left: 3px solid var(--accent);
}

/* ============ 动画区域 ============ */
.animation-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 28px;
  padding: 20px 0;
}

/* --- 呼吸圆形 --- */
.breath-circle-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 16px 0;
}

.breath-circle-container {
  position: relative;
  width: 180px;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.breath-circle {
  position: absolute;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle at 40% 35%, #7dd3fc 0%, #38bdf8 40%, #0ea5e9 100%);
  box-shadow: var(--shadow-glow), 0 0 60px rgba(14, 165, 233, 0.15);
  z-index: 3;
  will-change: transform;
}

.circle-inner {
  position: absolute;
  inset: 12%;
  border-radius: 50%;
  background: radial-gradient(circle at 45% 40%, rgba(255, 255, 255, 0.7) 0%, rgba(255, 255, 255, 0.15) 50%, transparent 70%);
  pointer-events: none;
}

.circle-glow {
  position: absolute;
  inset: -15%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(186, 230, 253, 0.4) 0%, transparent 70%);
  pointer-events: none;
  animation: glowPulse 3s ease-in-out infinite;
}

@keyframes glowPulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.circle-ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid rgba(14, 165, 233, 0.25);
  pointer-events: none;
  will-change: transform, opacity;
}

.ring-1 {
  width: 160px;
  height: 160px;
  z-index: 2;
}

.ring-2 {
  width: 200px;
  height: 200px;
  border-width: 1.5px;
  border-color: rgba(14, 165, 233, 0.15);
  z-index: 1;
}

/* --- 滑动滑块 --- */
.slider-track-wrapper {
  width: 100%;
  max-width: 500px;
  padding: 10px 30px;
  box-sizing: border-box;
}

.slider-track {
  position: relative;
  height: 50px;
  display: flex;
  align-items: center;
}

.track-line {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 6px;
  background: linear-gradient(90deg, #e2e8f0 0%, #cbd5e1 50%, #e2e8f0 100%);
  border-radius: 3px;
  transform: translateY(-50%);
}

.track-mark {
  position: absolute;
  top: 50%;
  width: 2px;
  height: 16px;
  background: #cbd5e1;
  border-radius: 1px;
  transform: translateY(-50%);
}

.track-mark-left {
  left: 6%;
}

.track-mark-right {
  right: 6%;
}

.track-end {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
}

.track-end-left {
  left: -2px;
}

.track-end-right {
  right: -2px;
}

.end-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #cbd5e1;
  border: 2px solid #e2e8f0;
}

.slider-thumb {
  position: absolute;
  top: 50%;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #38bdf8, #0ea5e9);
  box-shadow: 0 4px 15px rgba(14, 165, 233, 0.4), 0 0 0 4px rgba(14, 165, 233, 0.1);
  transform: translate(-50%, -50%);
  z-index: 5;
  will-change: left;
  transition: box-shadow 0.3s ease;
}

.thumb-inner {
  position: absolute;
  inset: 22%;
  border-radius: 50%;
  background: radial-gradient(circle at 40% 35%, rgba(255, 255, 255, 0.6), transparent);
  pointer-events: none;
}

/* ============ 底部完成提示 ============ */
.controls-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 0 16px;
}

.complete-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: var(--radius-md);
  padding: 10px 20px;
  color: #166534;
  font-weight: 600;
  font-size: 0.95rem;
  animation: bannerSlideIn 0.4s ease-out;
}

@keyframes bannerSlideIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.complete-icon {
  font-size: 1.3rem;
}

/* ============ 响应式设计 ============ */
@media (max-width: 600px) {
  .rowing-container {
    padding: 10px 12px;
    gap: 10px;
  }

  .stats-header {
    gap: 6px;
  }

  .stat-card {
    padding: 8px 10px;
    min-width: 60px;
    max-width: 100px;
    border-radius: var(--radius-sm);
  }

  .stat-label {
    font-size: 0.6rem;
  }

  .stat-value {
    font-size: 1.2rem;
  }

  .value-num {
    font-size: 1.2rem;
    min-width: 24px;
  }

  .breath-circle-container {
    width: 140px;
    height: 140px;
  }

  .breath-circle {
    width: 90px;
    height: 90px;
  }

  .ring-1 {
    width: 120px;
    height: 120px;
  }

  .ring-2 {
    width: 150px;
    height: 150px;
  }

  .slider-track-wrapper {
    padding: 10px 20px;
    max-width: 100%;
  }

  .slider-track {
    height: 40px;
  }

  .slider-thumb {
    width: 28px;
    height: 28px;
  }

  .track-line {
    height: 4px;
  }
}

@media (max-width: 380px) {
  .stats-header {
    gap: 4px;
  }

  .stat-card {
    padding: 6px 7px;
    min-width: 50px;
    max-width: 80px;
    border-radius: 6px;
  }

  .stat-value {
    font-size: 1rem;
  }

  .value-num {
    font-size: 1rem;
    min-width: 20px;
  }

  .breath-circle-container {
    width: 110px;
    height: 110px;
  }

  .breath-circle {
    width: 70px;
    height: 70px;
  }

  .ring-1 {
    width: 95px;
    height: 95px;
  }

  .ring-2 {
    width: 120px;
    height: 120px;
  }

  .slider-track-wrapper {
    padding: 8px 14px;
  }

  .slider-thumb {
    width: 24px;
    height: 24px;
  }
}

/* 暗色模式适配（保持亮色为主） */
@media (prefers-color-scheme: dark) {
  .rowing-page {
    --bg-primary: #1a1f2e;
    --bg-card: #252b3b;
    --text-primary: #e2e8f0;
    --text-secondary: #a0aec0;
    --text-muted: #718096;
    --slider-track: #3a4055;
  }

  .rowing-page {
    background: linear-gradient(160deg, #1a1f2e 0%, #1e2435 30%, #1a1f2e 70%, #1d2333 100%);
  }

  .stat-card {
    border-color: #2d3548;
  }

  .track-line {
    background: linear-gradient(90deg, #3a4055 0%, #4a5068 50%, #3a4055 100%);
  }

  .complete-banner {
    background: #1a2e1a;
    border-color: #2d5a2d;
    color: #86efac;
  }
}
</style>
