<template>
    <div class="rowing-machine">
        <!-- 左侧统计面板 -->
        <div class="stats-panel">
            <div class="stat-card" id="timerCard">
                <span class="stat-label">⏱ 运动时长</span>
                <span class="stat-value timer">{{ formattedTime }}</span>
            </div>
            <div class="stat-card resistance-card" id="resistanceCard">
                <span class="stat-label">⚙ 阻力档位</span>
                <div class="stat-controls">
                    <button class="btn-adjust decrement" @pointerdown.prevent="startLongPress(-1, changeResistance)"
                        @pointerup="stopLongPress" @pointerleave="stopLongPress" @pointercancel="stopLongPress"
                        @click.prevent>−</button>
                    <span class="value-display">{{ resistance }}</span>
                    <button class="btn-adjust increment" @pointerdown.prevent="startLongPress(1, changeResistance)"
                        @pointerup="stopLongPress" @pointerleave="stopLongPress" @pointercancel="stopLongPress"
                        @click.prevent>+</button>
                </div>
            </div>
            <div class="stat-card frequency-card" id="frequencyCard">
                <span class="stat-label">🔄 划桨频率 <span class="unit">(次/分)</span></span>
                <div class="stat-controls">
                    <button class="btn-adjust decrement" @pointerdown.prevent="startLongPress(-1, changeFrequency)"
                        @pointerup="stopLongPress" @pointerleave="stopLongPress" @pointercancel="stopLongPress"
                        @click.prevent>−</button>
                    <span class="value-display">{{ Math.round(displayFrequency) }}</span>
                    <button class="btn-adjust increment" @pointerdown.prevent="startLongPress(1, changeFrequency)"
                        @pointerup="stopLongPress" @pointerleave="stopLongPress" @pointercancel="stopLongPress"
                        @click.prevent>+</button>
                </div>
            </div>
            <button v-if="!exerciseEnded && elapsedSeconds > 0" class="end-btn" @click="endExercise">结束运动</button>
        </div>

        <!-- 右侧动画面板 -->
        <div class="animation-panel">
            <div class="breath-circle-wrapper">
                <div class="glow-layer glow-outer" ref="glowOuterRef"></div>
                <div class="glow-layer glow-mid" ref="glowMidRef"></div>
                <div class="breath-circle" ref="breathCircleRef">
                    <span class="breath-text" :class="currentBreathStage">{{ breathText }}</span>
                </div>
            </div>
        </div>

        <!-- 完成提示弹窗 -->
        <div v-if="showCompleteDialog" class="complete-overlay">
            <div class="complete-dialog">
                <p class="complete-title">🎉 运动计划已完成！</p>
                <p class="complete-desc">您已完成 {{ planTotalMinutes }} 分钟的训练</p>
                <div class="complete-actions">
                    <button class="dialog-btn continue-btn" @click="continueExercise">继续运动</button>
                    <button class="dialog-btn end-btn-dialog" @click="endExercise">结束运动</button>
                </div>
            </div>
        </div>

        <!-- 结束提示 -->
        <div v-if="showEndedMessage" class="complete-overlay">
            <div class="complete-dialog">
                <p class="complete-title">✅ 运动已记录</p>
                <p class="complete-desc">拉桨 {{ submittedStrokeCount }} 次 | 时长 {{ submittedTime }} 秒</p>
                <button class="dialog-btn continue-btn" @click="restartExercise">重新开始</button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import axios from 'axios';

// ---------- 类型定义 ----------
interface ExerciseRecord {
    type: string;
    time: number;
    extra: {
        stroke_count: number;
    };
}

interface PlanData {
    resistance: number[];
    frequency: number[];
}

// ---------- 响应式状态 ----------
const resistance = ref<number>(10);
const targetFrequency = ref<number>(20);
const displayFrequency = ref<number>(20);
const elapsedSeconds = ref<number>(0);
const strokeCount = ref<number>(0);
const currentBreathStage = ref<string>('inhale');
const breathText = ref<string>('吸气');
const showCompleteDialog = ref<boolean>(false);
const isCompleted = ref<boolean>(false);
const exerciseEnded = ref<boolean>(false);
const showEndedMessage = ref<boolean>(false);
const submittedStrokeCount = ref<number>(0);
const submittedTime = ref<number>(0);

// 计划数据
const planResistance = ref<number[]>([]);
const planFrequency = ref<number[]>([]);
const planTotalMinutes = computed(() => planResistance.value.length);
const planTotalSeconds = computed(() => planTotalMinutes.value * 60);

// 动画参数（非响应式提升性能，但需通过闭包访问）
let currentPeriod = 60 / 20; // 初始周期
let paramS = 0;
let prevBreathStage: string | null = null;
let animFrameId: number | null = null;
let lastFrameTime: number | null = null;
const PERIOD_SMOOTH_FACTOR = 6.5;
const FREQ_DISPLAY_SMOOTH = 5.0;
const ASYMMETRY_A = 0.40;
const SCALE_MIN = 0.38;
const SCALE_MAX = 1.0;
const GLOW_SCALE_MIN = 0.55;
const GLOW_SCALE_MAX = 1.0;
const GLOW_OPACITY_MIN = 0.35;
const GLOW_OPACITY_MAX = 0.85;

// DOM 引用
const breathCircleRef = ref<HTMLElement | null>(null);
const glowMidRef = ref<HTMLElement | null>(null);
const glowOuterRef = ref<HTMLElement | null>(null);

// 定时器
let timerInterval: ReturnType<typeof setInterval> | null = null;

// 长按相关
let longPressTimer: ReturnType<typeof setTimeout> | null = null;
let longPressInterval: ReturnType<typeof setInterval> | null = null;

// ---------- 计算属性 ----------
const formattedTime = computed(() => {
    const totalSec = Math.floor(elapsedSeconds.value);
    const hours = Math.floor(totalSec / 3600);
    const minutes = Math.floor((totalSec % 3600) / 60);
    const seconds = totalSec % 60;
    if (hours > 0) {
        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
});

// ---------- 辅助函数 ----------
const clamp = (val: number, min: number, max: number) => Math.max(min, Math.min(max, val));
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

const mapSToPhase = (s: number): number => {
    const twoPiS = 2 * Math.PI * s;
    return twoPiS + ASYMMETRY_A * Math.sin(twoPiS);
};

// ---------- 计划与记录请求 ----------
async function fetchPlan() {
    try {
        const response = await axios.get<PlanData>('exercise/plan/rowing');
        const data = response.data;
        if (data && Array.isArray(data.resistance) && Array.isArray(data.frequency) && data.resistance.length === data.frequency.length) {
            planResistance.value = data.resistance;
            planFrequency.value = data.frequency;
            // 初始化阻力与频率为第一分钟的计划值（如果计划存在）
            if (planResistance.value.length > 0) {
                resistance.value = planResistance.value[0];
                targetFrequency.value = planFrequency.value[0];
                currentPeriod = 60 / targetFrequency.value;
                displayFrequency.value = targetFrequency.value;
            }
        } else {
            planResistance.value = [];
            planFrequency.value = [];
        }
    } catch (error) {
        console.error('获取运动计划失败:', error);
        planResistance.value = [];
        planFrequency.value = [];
    }
}

async function submitRecord() {
    // 取整拉桨次数
    const strokes = Math.round(strokeCount.value);
    const time = Math.floor(elapsedSeconds.value);
    const payload: ExerciseRecord = {
        type: 'RowingMachine',
        time: time,
        extra: {
            stroke_count: strokes,
        },
    };
    try {
        await axios.post('exercise/record', payload);
        return { strokes, time };
    } catch (error) {
        console.error('提交运动记录失败:', error);
        // 仍然返回本地数据用于显示
        return { strokes, time };
    }
}

// ---------- 动画循环 ----------
function animate(timestamp: number) {
    if (lastFrameTime === null) {
        lastFrameTime = timestamp;
        animFrameId = requestAnimationFrame(animate);
        return;
    }
    let dt = (timestamp - lastFrameTime) / 1000;
    dt = Math.min(dt, 0.15);
    if (dt <= 0) dt = 0.001;
    lastFrameTime = timestamp;

    // 更新运动时长
    elapsedSeconds.value += dt;

    // 计划进度检查：自动按计划调整阻力/频率（基于当前分钟）
    const currentMinute = Math.floor(elapsedSeconds.value / 60);
    if (planResistance.value.length > 0 && currentMinute < planResistance.value.length) {
        const planR = planResistance.value[currentMinute];
        const planF = planFrequency.value[currentMinute];
        if (resistance.value !== planR) resistance.value = planR;
        if (targetFrequency.value !== planF) targetFrequency.value = planF;
    }

    // 周期平滑
    const targetPeriod = 60 / targetFrequency.value;
    const smoothFactor = 1 - Math.exp(-PERIOD_SMOOTH_FACTOR * dt);
    currentPeriod = lerp(currentPeriod, targetPeriod, smoothFactor);

    const actualFreq = 60 / currentPeriod;
    const freqSmooth = 1 - Math.exp(-FREQ_DISPLAY_SMOOTH * dt);
    displayFrequency.value = lerp(displayFrequency.value, actualFreq, freqSmooth);

    // 推进参数 s 并累计拉桨次数
    const ds = dt / currentPeriod;
    paramS += ds;
    strokeCount.value += ds; // 小数累加，提交时取整
    paramS = paramS - Math.floor(paramS);

    // 计算相位
    let phase = mapSToPhase(paramS);
    if (phase >= 2 * Math.PI) phase -= 2 * Math.PI;
    if (phase < 0) phase += 2 * Math.PI;

    // 呼吸因子 (1+cos)/2 : 0=收缩，1=扩张
    const cosPhase = Math.cos(phase);
    const breathFactor = (1 + cosPhase) / 2;
    const currentScale = SCALE_MIN + (SCALE_MAX - SCALE_MIN) * breathFactor;

    // 判断阶段
    const newStage = (phase > 0 && phase < Math.PI) ? 'exhale' : 'inhale';
    if (newStage !== prevBreathStage) {
        currentBreathStage.value = newStage;
        breathText.value = newStage === 'exhale' ? '呼气' : '吸气';
        prevBreathStage = newStage;
    }

    // 更新 DOM 元素样式
    if (breathCircleRef.value) {
        breathCircleRef.value.style.transform = `scale(${currentScale})`;
    }
    if (glowMidRef.value) {
        const glowScale = GLOW_SCALE_MIN + (GLOW_SCALE_MAX - GLOW_SCALE_MIN) * breathFactor;
        const glowOpacity = GLOW_OPACITY_MIN + (GLOW_OPACITY_MAX - GLOW_OPACITY_MIN) * breathFactor;
        glowMidRef.value.style.transform = `scale(${glowScale})`;
        glowMidRef.value.style.opacity = String(glowOpacity);
        if (glowOuterRef.value) {
            glowOuterRef.value.style.transform = `scale(${glowScale * 0.85 + 0.15})`;
            glowOuterRef.value.style.opacity = String(glowOpacity * 0.7);
        }
    }

    // 计划完成检测
    if (planTotalSeconds.value > 0 && elapsedSeconds.value >= planTotalSeconds.value && !isCompleted.value && !exerciseEnded.value) {
        isCompleted.value = true;
        showCompleteDialog.value = true;
    }

    animFrameId = requestAnimationFrame(animate);
}

function startAnimation() {
    if (animFrameId !== null) return;
    lastFrameTime = null;
    animFrameId = requestAnimationFrame(animate);
}

function stopAnimation() {
    if (animFrameId !== null) {
        cancelAnimationFrame(animFrameId);
        animFrameId = null;
    }
    lastFrameTime = null;
}

// ---------- 控制方法 ----------
function changeResistance(delta: number) {
    const newVal = clamp(resistance.value + delta, 1, 31);
    if (newVal !== resistance.value) {
        resistance.value = newVal;
        if (navigator.vibrate) navigator.vibrate(8);
    }
}

function changeFrequency(delta: number) {
    const newVal = clamp(targetFrequency.value + delta, 20, 28);
    if (newVal !== targetFrequency.value) {
        targetFrequency.value = newVal;
        if (navigator.vibrate) navigator.vibrate(6);
    }
}

function startLongPress(delta: number, fn: (d: number) => void) {
    fn(delta);
    stopLongPress(); // 清除之前的
    longPressTimer = setTimeout(() => {
        longPressInterval = setInterval(() => fn(delta), 80);
    }, 350);
}

function stopLongPress() {
    if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
    if (longPressInterval) { clearInterval(longPressInterval); longPressInterval = null; }
}

// ---------- 运动结束与重置 ----------
async function endExercise() {
    showCompleteDialog.value = false;
    stopAnimation();
    if (timerInterval) clearInterval(timerInterval);
    exerciseEnded.value = true;
    const { strokes, time } = await submitRecord();
    submittedStrokeCount.value = strokes;
    submittedTime.value = time;
    showEndedMessage.value = true;
}

function continueExercise() {
    showCompleteDialog.value = false;
    isCompleted.value = false; // 允许再次触发
}

async function restartExercise() {
    // 重置所有状态
    stopAnimation();
    if (timerInterval) clearInterval(timerInterval);
    elapsedSeconds.value = 0;
    strokeCount.value = 0;
    paramS = 0;
    currentBreathStage.value = 'inhale';
    breathText.value = '吸气';
    prevBreathStage = null;
    exerciseEnded.value = false;
    showEndedMessage.value = false;
    showCompleteDialog.value = false;
    isCompleted.value = false;

    // 重新获取计划
    await fetchPlan();

    // 启动动画与计时器
    timerInterval = setInterval(() => { }, 500); // 计时器仅用于强制更新视图？实际上动画循环中更新elapsedSeconds会触发响应式，不需要额外定时器，但保留之前逻辑也无妨
    startAnimation();
}

// ---------- 生命周期 ----------
onMounted(async () => {
    // 适配移动端横屏
    updateCircleBaseSize();
    window.addEventListener('resize', handleResize);

    // 获取计划并启动
    await fetchPlan();
    // 启动动画循环
    startAnimation();
});

onUnmounted(() => {
    stopAnimation();
    if (timerInterval) clearInterval(timerInterval);
    stopLongPress();
    window.removeEventListener('resize', handleResize);
});

// 响应式尺寸适配
function updateCircleBaseSize() {
    const vh = window.innerHeight;
    const vw = window.innerWidth;
    const isLandscape = vw > vh;
    let baseSize = isLandscape ? Math.min(vh * 0.55, vw * 0.38, 260) : Math.min(vh * 0.35, vw * 0.55, 200);
    baseSize = Math.max(baseSize, 90);
    if (breathCircleRef.value) {
        breathCircleRef.value.style.width = baseSize + 'px';
        breathCircleRef.value.style.height = baseSize + 'px';
    }
    if (glowMidRef.value) {
        glowMidRef.value.style.width = (baseSize * 1.2) + 'px';
        glowMidRef.value.style.height = (baseSize * 1.2) + 'px';
    }
    if (glowOuterRef.value) {
        glowOuterRef.value.style.width = (baseSize * 1.6) + 'px';
        glowOuterRef.value.style.height = (baseSize * 1.6) + 'px';
    }
}

let resizeDebounce: ReturnType<typeof setTimeout>;
function handleResize() {
    clearTimeout(resizeDebounce);
    resizeDebounce = setTimeout(updateCircleBaseSize, 200);
}
</script>

<style scoped>
.rowing-machine {
    width: 100%;
    height: 100%;
    max-width: 900px;
    max-height: 500px;
    display: flex;
    flex-direction: row;
    gap: 20px;
    padding: 18px;
    position: relative;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Helvetica Neue', sans-serif;
    background: linear-gradient(160deg, #faf7f3 0%, #f3f0ea 30%, #f7f4f0 60%, #faf8f5 100%);
    margin: 0 auto;
}

/* 左侧统计面板 */
.stats-panel {
    flex: 0 0 auto;
    width: 220px;
    min-width: 200px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    z-index: 2;
}

.stat-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
    display: flex;
    flex-direction: column;
    gap: 8px;
    position: relative;
    overflow: hidden;
}

.stat-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    border-radius: 0 4px 4px 0;
    opacity: 0.7;
}

.resistance-card::before {
    background: #e8917e;
}

.frequency-card::before {
    background: #5b9cb8;
}

.stat-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6b6b6b;
}

.stat-value {
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #2c2c2c;
    font-family: 'SF Mono', Menlo, Consolas, monospace;
    line-height: 1;
}

.stat-value.timer {
    font-size: 30px;
    letter-spacing: 0.03em;
}

.stat-controls {
    display: flex;
    align-items: center;
    gap: 10px;
}

.stat-controls .value-display {
    font-size: 24px;
    font-weight: 700;
    font-family: monospace;
    min-width: 40px;
    text-align: center;
    color: #2c2c2c;
}

.btn-adjust {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    border: 2px solid #e8e5e0;
    background: #fafaf8;
    color: #2c2c2c;
    font-size: 20px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
    outline: none;
    line-height: 1;
    flex-shrink: 0;
}

.btn-adjust:active {
    background: #e8e5e0;
    border-color: #d5d1ca;
    transform: scale(0.93);
}

.btn-adjust.decrement {
    color: #888;
}

.btn-adjust.increment {
    color: #3d7d99;
}

.unit {
    font-weight: 400;
    font-size: 10px;
}

/* 结束运动按钮 */
.end-btn {
    margin-top: 8px;
    background: #e8917e;
    color: white;
    border: none;
    border-radius: 20px;
    padding: 12px;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.05em;
    cursor: pointer;
    transition: background 0.2s;
}

.end-btn:active {
    background: #d47d6b;
}

/* 右侧动画面板 */
.animation-panel {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    min-width: 280px;
    z-index: 1;
}

.breath-circle-wrapper {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
}

.glow-layer {
    position: absolute;
    border-radius: 50%;
    pointer-events: none;
}

.glow-outer {
    background: radial-gradient(circle, rgba(139, 190, 210, 0.25) 0%, rgba(139, 190, 210, 0.06) 50%, transparent 70%);
    width: 320px;
    height: 320px;
    z-index: 0;
}

.glow-mid {
    background: radial-gradient(circle, rgba(160, 210, 225, 0.35) 0%, rgba(160, 210, 225, 0.10) 45%, transparent 65%);
    width: 240px;
    height: 240px;
    z-index: 1;
}

.breath-circle {
    position: relative;
    z-index: 2;
    width: 200px;
    height: 200px;
    border-radius: 50%;
    background: radial-gradient(circle at 38% 35%, #c5e8f5 0%, #8ecde5 18%, #5ba8c9 45%, #3d8aaa 70%, #2d708f 100%);
    box-shadow: 0 0 60px rgba(120, 185, 210, 0.35), 0 0 120px rgba(120, 185, 210, 0.15), 0 8px 32px rgba(0, 0, 0, 0.10), inset 0 -3px 8px rgba(0, 0, 0, 0.08), inset 0 3px 8px rgba(255, 255, 255, 0.30);
    display: flex;
    align-items: center;
    justify-content: center;
}

.breath-text {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: rgba(255, 255, 255, 0.92);
    text-shadow: 0 1px 4px rgba(0, 0, 0, 0.25);
    transition: opacity 0.15s;
    pointer-events: none;
    z-index: 3;
}

.breath-text.exhale {
    color: rgba(255, 240, 235, 0.95);
    text-shadow: 0 1px 6px rgba(180, 70, 50, 0.35);
}

.breath-text.inhale {
    color: rgba(240, 250, 255, 0.95);
    text-shadow: 0 1px 6px rgba(60, 130, 170, 0.35);
}

/* 弹窗样式 */
.complete-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(8px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
    border-radius: inherit;
}

.complete-dialog {
    background: white;
    border-radius: 24px;
    padding: 30px 24px;
    text-align: center;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
    max-width: 280px;
}

.complete-title {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 8px;
    color: #2c2c2c;
}

.complete-desc {
    font-size: 14px;
    color: #6b6b6b;
    margin-bottom: 20px;
}

.complete-actions {
    display: flex;
    gap: 12px;
    justify-content: center;
}

.dialog-btn {
    border: none;
    border-radius: 20px;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
}

.continue-btn {
    background: #5b9cb8;
    color: white;
}

.continue-btn:active {
    background: #4a8aa3;
}

.end-btn-dialog {
    background: #e8917e;
    color: white;
}

.end-btn-dialog:active {
    background: #d47d6b;
}

/* 响应式 */
@media (min-width: 768px) and (min-height: 500px) {
    .rowing-machine {
        max-height: 600px;
        gap: 28px;
        padding: 24px;
    }

    .stats-panel {
        width: 240px;
        gap: 14px;
    }

    .stat-card {
        padding: 18px 20px;
    }

    .stat-value {
        font-size: 32px;
    }

    .stat-value.timer {
        font-size: 34px;
    }

    .breath-circle {
        width: 240px;
        height: 240px;
    }

    .breath-text {
        font-size: 26px;
    }

    .glow-outer {
        width: 380px;
        height: 380px;
    }

    .glow-mid {
        width: 290px;
        height: 290px;
    }

    .btn-adjust {
        width: 42px;
        height: 42px;
        font-size: 22px;
    }
}

@media (max-width: 520px) or (max-height: 380px) {
    .rowing-machine {
        flex-direction: column;
        gap: 10px;
        padding: 10px;
        max-height: 100vh;
    }

    .stats-panel {
        flex-direction: row;
        width: 100%;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: center;
    }

    .stat-card {
        flex: 1;
        min-width: 90px;
        padding: 10px 12px;
        gap: 4px;
        border-radius: 10px;
    }

    .stat-value {
        font-size: 20px;
    }

    .stat-value.timer {
        font-size: 22px;
    }

    .stat-controls {
        gap: 6px;
    }

    .stat-controls .value-display {
        font-size: 18px;
        min-width: 30px;
    }

    .btn-adjust {
        width: 30px;
        height: 30px;
        font-size: 16px;
    }

    .breath-circle {
        width: 140px;
        height: 140px;
    }

    .breath-text {
        font-size: 17px;
    }

    .glow-outer {
        width: 220px;
        height: 220px;
    }

    .glow-mid {
        width: 170px;
        height: 170px;
    }

    .stat-label {
        font-size: 10px;
    }

    .animation-panel {
        min-width: auto;
        flex: 1;
    }
}

@media (max-height: 340px) {
    .breath-circle {
        width: 100px;
        height: 100px;
    }

    .breath-text {
        font-size: 14px;
    }

    .glow-outer {
        width: 160px;
        height: 160px;
    }

    .glow-mid {
        width: 125px;
        height: 125px;
    }

    .stat-value {
        font-size: 16px;
    }

    .stat-value.timer {
        font-size: 18px;
    }

    .stat-controls .value-display {
        font-size: 15px;
    }

    .btn-adjust {
        width: 26px;
        height: 26px;
        font-size: 14px;
    }
}
</style>
