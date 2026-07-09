<template>
    <!-- 选择页面 -->
    <div v-if="!currentSport" class="selection-page">
        <div class="logo">🏋️ 运动助手</div>
        <div class="subtitle">选择运动类型开始训练</div>
        <div class="card-container">
            <div class="sport-card rowing" @click="startSport('rowing')">
                <div class="icon-circle">🚣</div>
                <div class="card-info">
                    <h3>划船机</h3>
                    <span>横屏全屏 · 阻力调节 · 划桨节奏</span>
                </div>
            </div>
            <div class="sport-card running" @click="startSport('running')">
                <div class="icon-circle">🏃</div>
                <div class="card-info">
                    <h3>跑步</h3>
                    <span>竖屏使用 · 步频律动 · 实时计时</span>
                </div>
            </div>
            <div class="sport-card walking" @click="startSport('walking')">
                <div class="icon-circle">🚶</div>
                <div class="card-info">
                    <h3>快走</h3>
                    <span>竖屏使用 · 步频律动 · 实时计时</span>
                </div>
            </div>
        </div>
    </div>

    <!-- 划船机页面 -->
    <div v-if="currentSport === 'rowing'" class="sport-page rowing-page" :class="{ active: true }">
        <div class="stats-bar">
            <div class="stat-item">
                <span class="stat-label">运动时长</span>
                <span class="stat-value time">{{ formattedRowingTime }}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">阻力档位</span>
                <div class="stat-adjust">
                    <button class="adj-btn" @click="adjustResistance(-1)">−</button>
                    <span class="adj-val">{{ resistance }}</span>
                    <button class="adj-btn" @click="adjustResistance(1)">+</button>
                </div>
            </div>
            <div class="stat-item">
                <span class="stat-label">划桨频率</span>
                <div class="stat-adjust">
                    <button class="adj-btn" @click="adjustStrokeRate(-1)">−</button>
                    <span class="adj-val">{{ strokeRate }}</span>
                    <button class="adj-btn" @click="adjustStrokeRate(1)">+</button>
                </div>
            </div>
        </div>
        <div class="anim-area" ref="rowingAnimArea">
            <canvas ref="rowingCanvasRef" class="rowing-canvas"></canvas>
        </div>
        <div class="btn-bar">
            <button class="btn btn-pause" :class="{ paused: isPaused }" @click="togglePause">
                {{ isPaused ? '▶ 继续' : '⏸ 暂停' }}
            </button>
            <button class="btn btn-end" @click="endSport">⏹ 结束运动</button>
        </div>
    </div>

    <!-- 跑步页面 -->
    <div v-if="currentSport === 'running'" class="sport-page running-page" :class="{ active: true }">
        <div class="stats-bar">
            <div class="stat-item">
                <span class="stat-label">运动时长</span>
                <span class="stat-value time">{{ formattedRunningTime }}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">当前时间</span>
                <span class="stat-value">{{ currentClock }}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">步频</span>
                <div class="stat-adjust">
                    <button class="adj-btn" @click="adjustCadence('running', -1)">−</button>
                    <span class="adj-val">{{ runningCadence }}</span>
                    <button class="adj-btn" @click="adjustCadence('running', 1)">+</button>
                </div>
            </div>
        </div>
        <div class="anim-area">
            <div class="cadence-area">
                <div class="foot-wrapper">
                    <div class="foot-indicator" ref="runningFootLeft"></div>
                    <span class="foot-label">左</span>
                </div>
                <div class="foot-wrapper">
                    <div class="foot-indicator" ref="runningFootRight"></div>
                    <span class="foot-label">右</span>
                </div>
            </div>
        </div>
        <div class="btn-bar">
            <button class="btn btn-pause" :class="{ paused: isPaused }" @click="togglePause">
                {{ isPaused ? '▶ 继续' : '⏸ 暂停' }}
            </button>
            <button class="btn btn-end" @click="endSport">⏹ 结束运动</button>
        </div>
    </div>

    <!-- 快走页面 -->
    <div v-if="currentSport === 'walking'" class="sport-page walking-page" :class="{ active: true }">
        <div class="stats-bar">
            <div class="stat-item">
                <span class="stat-label">运动时长</span>
                <span class="stat-value time">{{ formattedWalkingTime }}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">当前时间</span>
                <span class="stat-value">{{ currentClock }}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">步频</span>
                <div class="stat-adjust">
                    <button class="adj-btn" @click="adjustCadence('walking', -1)">−</button>
                    <span class="adj-val">{{ walkingCadence }}</span>
                    <button class="adj-btn" @click="adjustCadence('walking', 1)">+</button>
                </div>
            </div>
        </div>
        <div class="anim-area">
            <div class="cadence-area">
                <div class="foot-wrapper">
                    <div class="foot-indicator" ref="walkingFootLeft"></div>
                    <span class="foot-label">左</span>
                </div>
                <div class="foot-wrapper">
                    <div class="foot-indicator" ref="walkingFootRight"></div>
                    <span class="foot-label">右</span>
                </div>
            </div>
        </div>
        <div class="btn-bar">
            <button class="btn btn-pause" :class="{ paused: isPaused }" @click="togglePause">
                {{ isPaused ? '▶ 继续' : '⏸ 暂停' }}
            </button>
            <button class="btn btn-end" @click="endSport">⏹ 结束运动</button>
        </div>
    </div>

    <!-- 旋转提示 -->
    <div v-if="showRotateHint" class="rotate-hint" @click="dismissRotateHint">
        <div class="rotate-icon">↻</div>
        <div>请将设备旋转至横屏<br>以使用划船机功能</div>
    </div>

    <!-- 结束运动弹窗 -->
    <div v-if="endModalVisible" class="end-modal-overlay" @click.self="closeEndModal">
        <div class="end-modal">
            <h3>🏁 结束运动</h3>
            <div class="modal-subtitle">{{ currentSportName }}</div>
            <div class="summary-row">
                <span>运动时长</span>
                <span class="val">{{ formattedDuration }}</span>
            </div>
            <div class="summary-row" v-if="extraSummary">
                <span>{{ extraSummary.label }}</span>
                <span class="val">{{ extraSummary.value }}</span>
            </div>
            <div class="input-group">
                <label>{{ inputLabel }}</label>
                <input type="number" v-model.number="endInputValue" inputmode="numeric" :min="0" :step="inputStep" />
            </div>
            <div class="modal-btns">
                <button class="btn btn-cancel" @click="closeEndModal">取消</button>
                <button class="btn btn-confirm" @click="confirmEnd">确认提交</button>
            </div>
        </div>
    </div>

    <!-- 计划完成提示弹窗 -->
    <div v-if="planCompletedModal" class="end-modal-overlay" @click.self="continueAfterPlan">
        <div class="end-modal">
            <h3>🎉 运动计划完成</h3>
            <div class="modal-subtitle">{{ currentSportName }}</div>
            <p style="text-align: center; margin: 16px 0; color: #ccc;">
                您已完成 {{ totalPlanMinutes }} 分钟的计划运动，是否继续？
            </p>
            <div class="modal-btns">
                <button class="btn btn-cancel" @click="continueAfterPlan">继续运动</button>
                <button class="btn btn-confirm" @click="handlePlanCompletedEnd">结束运动</button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import axios from 'axios';

// ==================== 类型定义 ====================
type SportType = 'rowing' | 'running' | 'walking' | null;
interface RowingPlan {
    resistance: number[];
    frequency: number[];
}
interface CadencePlan {
    frequency: number[];
}
interface ExtraSummary {
    label: string;
    value: string;
}

// ==================== 状态 ====================
const currentSport = ref<SportType>(null);
const isPaused = ref(false);
const timerInterval = ref<number | null>(null);
const animFrameId = ref<number | null>(null);
const startTimestamp = ref(0);
const elapsedSeconds = ref(0);
const pauseOffset = ref(0);
const resistance = ref(10);
const strokeRate = ref(20);
const strokeCount = ref(0);
const runningCadence = ref(80);
const walkingCadence = ref(60);
const rowingPhase = ref<'drive' | 'recovery'>('recovery');
const rowingSeatX = ref(0);
const rowingFlywheelAngle = ref(0);
const rowingCycleStartTime = ref(0);
const currentClock = ref('--:--:--');
const showRotateHint = ref(false);
const orientationLocked = ref(false);

// 计划数据
const rowingPlan = ref<RowingPlan | null>(null);
const runningPlan = ref<CadencePlan | null>(null);
const walkingPlan = ref<CadencePlan | null>(null);
const totalPlanMinutes = ref(0); // 计划总分钟数
const planCompletedShown = ref(false); // 防止重复弹窗

// 结束弹窗
const endModalVisible = ref(false);
const endInputValue = ref<number>(0);
const inputLabel = ref('');
const inputStep = ref(1);
const extraSummary = ref<ExtraSummary | null>(null);
const planCompletedModal = ref(false);

// Canvas refs
const rowingCanvasRef = ref<HTMLCanvasElement | null>(null);
const rowingAnimArea = ref<HTMLDivElement | null>(null);
// 律动脚部 refs
const runningFootLeft = ref<HTMLDivElement | null>(null);
const runningFootRight = ref<HTMLDivElement | null>(null);
const walkingFootLeft = ref<HTMLDivElement | null>(null);
const walkingFootRight = ref<HTMLDivElement | null>(null);

// 计算属性
const formattedRowingTime = computed(() => formatDuration(elapsedSeconds.value));
const formattedRunningTime = computed(() => formatDuration(elapsedSeconds.value));
const formattedWalkingTime = computed(() => formatDuration(elapsedSeconds.value));
const formattedDuration = computed(() => formatDuration(elapsedSeconds.value));
const currentSportName = computed(() => {
    switch (currentSport.value) {
        case 'rowing': return '划船机';
        case 'running': return '跑步';
        case 'walking': return '快走';
        default: return '';
    }
});

// ==================== 工具函数 ====================
function formatDuration(totalSec: number): string {
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    const pad = (n: number) => String(n).padStart(2, '0');
    if (h > 0) return `${pad(h)}:${pad(m)}:${pad(s)}`;
    return `${pad(m)}:${pad(s)}`;
}

// ==================== 时钟更新 ====================
function updateClock() {
    const now = new Date();
    currentClock.value = now.toLocaleTimeString('zh-CN', { hour12: false });
}

// ==================== 计时器 ====================
function startTimer() {
    stopTimer();
    startTimestamp.value = Date.now() - pauseOffset.value;
    timerInterval.value = window.setInterval(() => {
        if (!isPaused.value) {
            elapsedSeconds.value = Math.floor((Date.now() - startTimestamp.value) / 1000);
            updateClock();
            checkPlanCompletion();
        }
    }, 200);
}

function stopTimer() {
    if (timerInterval.value) {
        clearInterval(timerInterval.value);
        timerInterval.value = null;
    }
}

// ==================== 计划完成检测 ====================
function checkPlanCompletion() {
    if (totalPlanMinutes.value <= 0 || planCompletedShown.value) return;
    const plannedSeconds = totalPlanMinutes.value * 60;
    if (elapsedSeconds.value >= plannedSeconds) {
        planCompletedShown.value = true;
        planCompletedModal.value = true;
        // 暂停运动
        isPaused.value = true;
        stopTimer();
        if (animFrameId.value) {
            cancelAnimationFrame(animFrameId.value);
            animFrameId.value = null;
        }
    }
}

function continueAfterPlan() {
    planCompletedModal.value = false;
    // 不重置计划完成标记，继续运动但不再提示
    isPaused.value = false;
    startTimer();
    restartAnimations();
}

function handlePlanCompletedEnd() {
    planCompletedModal.value = false;
    // 显示结束弹窗
    showEndModal();
}

// ==================== 动画重启 ====================
function restartAnimations() {
    if (currentSport.value === 'rowing') {
        rowingCycleStartTime.value = performance.now();
        startRowingAnimation();
    } else if (currentSport.value === 'running' || currentSport.value === 'walking') {
        startCadenceAnimation();
    }
}

// ==================== 运动开始/结束 ====================
async function startSport(type: SportType) {
    if (!type) return;
    currentSport.value = type;
    // 重置状态
    isPaused.value = false;
    elapsedSeconds.value = 0;
    pauseOffset.value = 0;
    strokeCount.value = 0;
    planCompletedShown.value = false;
    totalPlanMinutes.value = 0;
    rowingPlan.value = null;
    runningPlan.value = null;
    walkingPlan.value = null;

    // 获取计划
    if (type === 'rowing') {
        try {
            const { data } = await axios.get<RowingPlan>('/exercise/plan/rowing');
            if (data && data.resistance && data.frequency) {
                rowingPlan.value = data;
                totalPlanMinutes.value = data.resistance.length;
                // 初始设置为第一分钟的值
                if (data.resistance.length > 0) {
                    resistance.value = data.resistance[0];
                    strokeRate.value = data.frequency[0];
                }
            }
        } catch (e) {
            console.warn('获取划船机计划失败，使用默认值');
        }
        showRotateHint.value = true;
        setupRowingOrientation();
        await nextTick();
        resizeRowingCanvas();
        rowingCycleStartTime.value = performance.now();
        startRowingAnimation();
    } else if (type === 'running') {
        try {
            const { data } = await axios.get<CadencePlan>('/exercise/plan/running');
            if (data && data.frequency) {
                runningPlan.value = data;
                totalPlanMinutes.value = data.frequency.length;
                if (data.frequency.length > 0) {
                    runningCadence.value = data.frequency[0];
                }
            }
        } catch (e) {
            console.warn('获取跑步计划失败');
        }
        startCadenceAnimation();
    } else if (type === 'walking') {
        try {
            const { data } = await axios.get<CadencePlan>('/exercise/plan/walking');
            if (data && data.frequency) {
                walkingPlan.value = data;
                totalPlanMinutes.value = data.frequency.length;
                if (data.frequency.length > 0) {
                    walkingCadence.value = data.frequency[0];
                }
            }
        } catch (e) {
            console.warn('获取快走计划失败');
        }
        startCadenceAnimation();
    }

    startTimer();
    updateClock();
}

function endSport() {
    // 停止计时和动画
    isPaused.value = true;
    stopTimer();
    if (animFrameId.value) {
        cancelAnimationFrame(animFrameId.value);
        animFrameId.value = null;
    }
    showEndModal();
}

function showEndModal() {
    endModalVisible.value = true;
    endInputValue.value = 0;
    if (currentSport.value === 'rowing') {
        inputLabel.value = '划桨次数';
        inputStep.value = 1;
        endInputValue.value = Math.floor(elapsedSeconds.value / 60 * strokeRate.value);
        extraSummary.value = {
            label: '阻力档位 / 频率',
            value: `${resistance.value}档 / ${strokeRate.value}次/分`
        };
    } else {
        inputLabel.value = '运动距离 (公里)';
        inputStep.value = 0.01;
        endInputValue.value = 0;
        extraSummary.value = currentSport.value === 'running' ? {
            label: '步频',
            value: `${runningCadence.value} 步/分`
        } : {
            label: '步频',
            value: `${walkingCadence.value} 步/分`
        };
    }
}

function closeEndModal() {
    endModalVisible.value = false;
    // 如果之前是从计划完成跳转过来的，继续保持暂停？用户取消后恢复运动
    isPaused.value = false;
    startTimer();
    restartAnimations();
}

async function confirmEnd() {
    endModalVisible.value = false;
    const sportType = currentSport.value;
    if (!sportType) return;

    const payload: any = {
        type: sportType === 'rowing' ? 'RowingMachine' : sportType === 'running' ? 'Running' : 'BriskWalking',
        time: elapsedSeconds.value,
        extra: {}
    };

    if (sportType === 'rowing') {
        payload.extra = { stroke_count: endInputValue.value };
    } else {
        payload.extra = { distance: endInputValue.value };
    }

    try {
        await axios.post('/exercise/record', payload);
        console.log('数据提交成功', payload);
        alert('✅ 运动数据已记录！');
    } catch (e) {
        console.error('提交失败', e);
        alert('提交失败，请重试');
    }

    // 重置所有状态
    cleanup();
    currentSport.value = null;
}

// ==================== 清理 ====================
function cleanup() {
    stopTimer();
    if (animFrameId.value) {
        cancelAnimationFrame(animFrameId.value);
        animFrameId.value = null;
    }
    clearRowingOrientation();
    showRotateHint.value = false;
    // 重置脚部动画元素
    resetFootElements();
}

function resetFootElements() {
    [runningFootLeft, runningFootRight, walkingFootLeft, walkingFootRight].forEach(ref => {
        if (ref.value) ref.value.style.transform = 'translateY(0px)';
    });
}

// ==================== 暂停/继续 ====================
function togglePause() {
    if (!currentSport.value) return;
    isPaused.value = !isPaused.value;
    if (isPaused.value) {
        pauseOffset.value = Date.now() - startTimestamp.value;
        stopTimer();
        if (animFrameId.value) {
            cancelAnimationFrame(animFrameId.value);
            animFrameId.value = null;
        }
    } else {
        startTimestamp.value = Date.now() - pauseOffset.value;
        startTimer();
        restartAnimations();
    }
}

// ==================== 参数调整 ====================
function adjustResistance(delta: number) {
    if (currentSport.value !== 'rowing') return;
    resistance.value = Math.max(1, Math.min(31, resistance.value + delta));
}

function adjustStrokeRate(delta: number) {
    if (currentSport.value !== 'rowing') return;
    strokeRate.value = Math.max(20, Math.min(28, strokeRate.value + delta));
    rowingCycleStartTime.value = performance.now();
}

function adjustCadence(type: 'running' | 'walking', delta: number) {
    if (currentSport.value !== type) return;
    if (type === 'running') {
        runningCadence.value = Math.max(40, Math.min(120, runningCadence.value + delta));
    } else {
        walkingCadence.value = Math.max(30, Math.min(100, walkingCadence.value + delta));
    }
}

// ==================== 计划每分钟更新 ====================
// 监听 elapsedSeconds 的变化，在每分钟开始时根据计划更新参数
watch(elapsedSeconds, (newVal) => {
    const minute = Math.floor(newVal / 60);
    if (minute <= 0) return;

    if (currentSport.value === 'rowing' && rowingPlan.value) {
        const plan = rowingPlan.value;
        if (minute < plan.resistance.length) {
            // 自动设置为计划值（覆盖用户当前设置）
            resistance.value = plan.resistance[minute];
            strokeRate.value = plan.frequency[minute];
        }
    } else if (currentSport.value === 'running' && runningPlan.value) {
        const plan = runningPlan.value;
        if (minute < plan.frequency.length) {
            runningCadence.value = plan.frequency[minute];
        }
    } else if (currentSport.value === 'walking' && walkingPlan.value) {
        const plan = walkingPlan.value;
        if (minute < plan.frequency.length) {
            walkingCadence.value = plan.frequency[minute];
        }
    }
});

// ==================== 划船机动画 ====================
function startRowingAnimation() {
    if (animFrameId.value) cancelAnimationFrame(animFrameId.value);
    if (isPaused.value || currentSport.value !== 'rowing') return;

    const animate = (timestamp: number) => {
        if (isPaused.value || currentSport.value !== 'rowing') {
            animFrameId.value = null;
            return;
        }
        updateRowingAnimation(timestamp);
        drawRowingScene();
        animFrameId.value = requestAnimationFrame(animate);
    };
    animFrameId.value = requestAnimationFrame(animate);
}

function updateRowingAnimation(timestamp: number) {
  const cycleDuration = (60 / strokeRate.value) * 1000;
  const driveRatio = 0.35; // 拉桨时间占比35%
  // 计算当前周期内的全局进度 (0~1)
  const globalT = ((timestamp - rowingCycleStartTime.value) % cycleDuration) / cycleDuration;

  let seatX: number;
  let phaseLabel: 'drive' | 'recovery';

  // 根据全局进度判断当前所处的阶段（用于箭头文字显示）
  if (globalT < driveRatio) {
    phaseLabel = 'drive';
  } else {
    phaseLabel = 'recovery';
  }
  rowingPhase.value = phaseLabel;

  // 使用分段三次平滑过渡函数（smoothstep）计算座位位置
  // 保证在阶段切换点（globalT=0、globalT=driveRatio、globalT=1）速度为零
  if (globalT < driveRatio) {
    // 拉桨阶段：座位从近端(0)移向远端(1)，两端速度为零
    const s = globalT / driveRatio; // 将阶段进度映射到0~1
    seatX = 3 * s * s - 2 * s * s * s; // smoothstep: 0→1
  } else {
    // 复位阶段：座位从远端(1)移回近端(0)，两端速度为零
    const s = (globalT - driveRatio) / (1 - driveRatio); // 映射到0~1
    seatX = 1 - (3 * s * s - 2 * s * s * s); // smoothstep: 1→0
  }
  rowingSeatX.value = seatX;

  // 飞轮旋转逻辑基本不变，仍然根据阻力档位调整基础转速
  if (globalT < driveRatio) {
    const driveProgress = globalT / driveRatio;
    const driveSpeed = 0.1 + (resistance.value / 31) * 0.15;
    rowingFlywheelAngle.value += driveSpeed * (1 + driveProgress * 0.15);
  } else {
    const recoverySpeed = 0.1 + (resistance.value / 31) * 0.05;
    rowingFlywheelAngle.value += recoverySpeed;
  }

  // 累计划桨次数（基于运动时长和频率）
  strokeCount.value = Math.floor(elapsedSeconds.value / (60 / strokeRate.value));
}


function drawRowingScene() {
    const canvas = rowingCanvasRef.value;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const logicalW = w / dpr;
    const logicalH = h / dpr;
    ctx.save();
    ctx.scale(dpr, dpr);

    // 背景
    const bgGrad = ctx.createLinearGradient(0, 0, 0, logicalH);
    bgGrad.addColorStop(0, '#0f1f2e');
    bgGrad.addColorStop(0.5, '#0d1a24');
    bgGrad.addColorStop(1, '#0a141c');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, logicalW, logicalH);

    const marginX = logicalW * 0.06;
    const marginY = logicalH * 0.1;
    const availableW = logicalW - 2 * marginX;
    const availableH = logicalH - 2 * marginY;
    const trackY = logicalH * 0.55;
    const trackLength = availableW * 0.68;
    const trackStartX = marginX + availableW * 0.16;
    const trackEndX = trackStartX + trackLength;

    // 飞轮
    const flywheelCX = marginX + availableW * 0.1;
    const flywheelCY = trackY;
    const flywheelRadius = Math.min(availableH * 0.32, availableW * 0.12);
    const glowGrad = ctx.createRadialGradient(flywheelCX, flywheelCY, flywheelRadius * 0.7, flywheelCX, flywheelCY, flywheelRadius * 1.5);
    glowGrad.addColorStop(0, 'rgba(100,200,240,0.25)');
    glowGrad.addColorStop(0.5, 'rgba(40,120,180,0.1)');
    glowGrad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = glowGrad;
    ctx.beginPath();
    ctx.arc(flywheelCX, flywheelCY, flywheelRadius * 1.5, 0, Math.PI * 2);
    ctx.fill();

    const wheelGrad = ctx.createRadialGradient(flywheelCX - flywheelRadius * 0.2, flywheelCY - flywheelRadius * 0.2, flywheelRadius * 0.1, flywheelCX, flywheelCY, flywheelRadius);
    wheelGrad.addColorStop(0, '#5cb8d8');
    wheelGrad.addColorStop(0.6, '#1a5a7a');
    wheelGrad.addColorStop(1, '#0d3045');
    ctx.fillStyle = wheelGrad;
    ctx.beginPath();
    ctx.arc(flywheelCX, flywheelCY, flywheelRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = 'rgba(150,220,250,0.5)';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    for (let i = 0; i < 8; i++) {
        const angle = rowingFlywheelAngle.value + (i / 8) * Math.PI * 2;
        const innerR = flywheelRadius * 0.2;
        const outerR = flywheelRadius * 0.85;
        ctx.strokeStyle = 'rgba(180,230,250,0.45)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(flywheelCX + Math.cos(angle) * innerR, flywheelCY + Math.sin(angle) * innerR);
        ctx.lineTo(flywheelCX + Math.cos(angle) * outerR, flywheelCY + Math.sin(angle) * outerR);
        ctx.stroke();
    }
    ctx.fillStyle = '#cde8f4';
    ctx.beginPath();
    ctx.arc(flywheelCX, flywheelCY, flywheelRadius * 0.1, 0, Math.PI * 2);
    ctx.fill();

    // 轨道
    ctx.fillStyle = '#1a3040';
    ctx.fillRect(trackStartX, trackY - 3, trackLength, 6);
    const railGrad = ctx.createLinearGradient(0, trackY - 3, 0, trackY + 3);
    railGrad.addColorStop(0, 'rgba(120,180,210,0.4)');
    railGrad.addColorStop(0.5, 'rgba(200,230,250,0.7)');
    railGrad.addColorStop(1, 'rgba(80,140,180,0.4)');
    ctx.fillStyle = railGrad;
    ctx.fillRect(trackStartX, trackY - 1.5, trackLength, 3);
    // 端点
    ctx.fillStyle = 'rgba(150,200,230,0.6)';
    ctx.beginPath();
    ctx.arc(trackStartX, trackY, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(trackEndX, trackY, 5, 0, Math.PI * 2);
    ctx.fill();

    // 座位
    const seatX = trackStartX + rowingSeatX.value * trackLength;
    const seatW = Math.min(availableW * 0.06, 36);
    const seatH = Math.min(availableH * 0.18, 28);
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.beginPath();
    ctx.roundRect(seatX - seatW / 2 + 2, trackY - seatH / 2 + 2, seatW, seatH, 8);
    ctx.fill();
    const seatGrad = ctx.createLinearGradient(0, trackY - seatH / 2, 0, trackY + seatH / 2);
    seatGrad.addColorStop(0, '#445566');
    seatGrad.addColorStop(0.5, '#2a3a4a');
    seatGrad.addColorStop(1, '#1a2835');
    ctx.fillStyle = seatGrad;
    ctx.beginPath();
    ctx.roundRect(seatX - seatW / 2, trackY - seatH / 2, seatW, seatH, 8);
    ctx.fill();
    ctx.strokeStyle = 'rgba(180,210,240,0.5)';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = 'rgba(200,220,240,0.35)';
    ctx.fillRect(seatX - seatW / 2 + 4, trackY - seatH / 2 + 3, seatW - 8, seatH * 0.3);

    // 拉绳
    ctx.strokeStyle = 'rgba(200,220,240,0.55)';
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    ctx.moveTo(flywheelCX + flywheelRadius * 0.3, flywheelCY);
    ctx.lineTo(seatX, trackY - seatH / 2 - 2);
    ctx.stroke();
    ctx.setLineDash([]);

    // 手柄
    const handleW = seatW * 0.8;
    ctx.fillStyle = '#3a4a5a';
    ctx.beginPath();
    ctx.roundRect(seatX - handleW / 2, trackY - seatH / 2 - 14, handleW, 10, 5);
    ctx.fill();
    ctx.strokeStyle = 'rgba(200,220,240,0.6)';
    ctx.lineWidth = 2;
    ctx.stroke();

    // 箭头
    // if (rowingPhase.value === 'drive') {
    //     ctx.fillStyle = 'rgba(255,200,100,0.85)';
    //     ctx.font = 'bold 13px sans-serif';
    //     ctx.fillText('→ 拉桨', seatX + seatW / 2 + 10, trackY - seatH / 2 - 20);
    // } else {
    //     ctx.fillStyle = 'rgba(150,200,220,0.65)';
    //     ctx.font = 'bold 13px sans-serif';
    //     ctx.fillText('← 复位', seatX - seatW / 2 - 55, trackY - seatH / 2 - 20);
    // }

    ctx.restore();
}

function resizeRowingCanvas() {
    if (!rowingCanvasRef.value || !rowingAnimArea.value) return;
    const container = rowingAnimArea.value;
    const rect = container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    rowingCanvasRef.value.width = rect.width * dpr;
    rowingCanvasRef.value.height = rect.height * dpr;
    rowingCanvasRef.value.style.width = rect.width + 'px';
    rowingCanvasRef.value.style.height = rect.height + 'px';
}

// ==================== 律动动画 ====================
function startCadenceAnimation() {
    if (animFrameId.value) cancelAnimationFrame(animFrameId.value);
    if (isPaused.value || (currentSport.value !== 'running' && currentSport.value !== 'walking')) return;

    const animate = (timestamp: number) => {
        if (isPaused.value || (currentSport.value !== 'running' && currentSport.value !== 'walking')) {
            animFrameId.value = null;
            return;
        }
        updateCadenceAnimation(timestamp);
        animFrameId.value = requestAnimationFrame(animate);
    };
    animFrameId.value = requestAnimationFrame(animate);
}

function updateCadenceAnimation(timestamp: number) {
    const cadence = currentSport.value === 'running' ? runningCadence.value : walkingCadence.value;
    const cycleMs = (60 / cadence) * 1000;
    const phase = (timestamp % cycleMs) / cycleMs;
    const leftHeight = Math.sin(phase * Math.PI * 2) * 0.5 + 0.5;
    const rightHeight = Math.sin((phase + 0.5) * Math.PI * 2) * 0.5 + 0.5;
    const maxOffset = 28;
    const leftOffset = (1 - leftHeight) * maxOffset;
    const rightOffset = (1 - rightHeight) * maxOffset;

    if (currentSport.value === 'running') {
        if (runningFootLeft.value) runningFootLeft.value.style.transform = `translateY(${leftOffset}px)`;
        if (runningFootRight.value) runningFootRight.value.style.transform = `translateY(${rightOffset}px)`;
    } else if (currentSport.value === 'walking') {
        if (walkingFootLeft.value) walkingFootLeft.value.style.transform = `translateY(${leftOffset}px)`;
        if (walkingFootRight.value) walkingFootRight.value.style.transform = `translateY(${rightOffset}px)`;
    }
}

// ==================== 横屏处理 ====================
function setupRowingOrientation() {
    orientationLocked.value = false;
    if (screen.orientation && screen.orientation.lock) {
        screen.orientation.lock('landscape').then(() => {
            orientationLocked.value = true;
            showRotateHint.value = false;
        }).catch(() => {
            checkOrientation();
        });
    } else if ((screen as any).lockOrientation) {
        try {
            (screen as any).lockOrientation('landscape');
            orientationLocked.value = true;
            showRotateHint.value = false;
        } catch (e) {
            checkOrientation();
        }
    } else {
        checkOrientation();
    }
    window.addEventListener('orientationchange', handleOrientationChange);
    window.addEventListener('resize', handleOrientationChange);
}

function clearRowingOrientation() {
    window.removeEventListener('orientationchange', handleOrientationChange);
    window.removeEventListener('resize', handleOrientationChange);
    orientationLocked.value = false;
    showRotateHint.value = false;
}

function handleOrientationChange() {
    if (currentSport.value !== 'rowing') return;
    checkOrientation();
    resizeRowingCanvas();
}

function checkOrientation() {
    const isPortrait = window.innerWidth <= window.innerHeight;
    if (isPortrait && !orientationLocked.value) {
        showRotateHint.value = true;
    } else {
        showRotateHint.value = false;
    }
}

function dismissRotateHint() {
    showRotateHint.value = false;
}

// ==================== 生命周期 ====================
onMounted(() => {
    updateClock();
    window.addEventListener('resize', onResize);
});

onUnmounted(() => {
    stopTimer();
    if (animFrameId.value) cancelAnimationFrame(animFrameId.value);
    window.removeEventListener('resize', onResize);
    clearRowingOrientation();
});

function onResize() {
    if (currentSport.value === 'rowing') {
        resizeRowingCanvas();
    }
}
</script>

<style scoped>
/* 所有样式与原始CSS完全一致，仅将全局选择器改为scoped，并保持原有结构 */
:root {
    --safe-top: env(safe-area-inset-top, 0px);
    --safe-bottom: env(safe-area-inset-bottom, 0px);
    --safe-left: env(safe-area-inset-left, 0px);
    --safe-right: env(safe-area-inset-right, 0px);
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    -webkit-tap-highlight-color: transparent;
    -webkit-user-select: none;
    user-select: none;
    -webkit-touch-callout: none;
}

.selection-page {
    position: fixed;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(160deg, #0f0f1a 0%, #1a1a2e 40%, #0d0d18 100%);
    z-index: 100;
    padding: 20px;
    transition: opacity 0.4s, transform 0.4s;
}

.logo {
    font-size: 2rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 8px;
    letter-spacing: 2px;
}

.subtitle {
    font-size: 0.9rem;
    color: #888;
    margin-bottom: 40px;
    letter-spacing: 1px;
}

.card-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
    width: 100%;
    max-width: 340px;
}

.sport-card {
    position: relative;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 22px 20px;
    border-radius: 18px;
    cursor: pointer;
    transition: all 0.25s;
    border: 2px solid transparent;
    background: rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(6px);
}

.sport-card:active {
    transform: scale(0.96);
    opacity: 0.85;
}

.sport-card.rowing {
    border-color: rgba(64, 180, 220, 0.5);
    background: rgba(30, 100, 140, 0.15);
}

.sport-card.running {
    border-color: rgba(255, 140, 60, 0.5);
    background: rgba(180, 80, 20, 0.15);
}

.sport-card.walking {
    border-color: rgba(100, 210, 130, 0.5);
    background: rgba(30, 130, 60, 0.15);
}

.icon-circle {
    width: 52px;
    height: 52px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.6rem;
    flex-shrink: 0;
}

.sport-card.rowing .icon-circle {
    background: rgba(64, 180, 220, 0.25);
}

.sport-card.running .icon-circle {
    background: rgba(255, 140, 60, 0.25);
}

.sport-card.walking .icon-circle {
    background: rgba(100, 210, 130, 0.25);
}

.card-info h3 {
    font-size: 1.15rem;
    color: #fff;
    font-weight: 600;
}

.card-info span {
    font-size: 0.78rem;
    color: #999;
}

/* 运动页面通用样式 */
.sport-page {
    position: fixed;
    inset: 0;
    display: none;
    flex-direction: column;
    z-index: 90;
    background: #0d0d16;
    color: #fff;
}

.sport-page.active {
    display: flex;
}

.stats-bar {
    display: flex;
    align-items: center;
    justify-content: space-around;
    flex-wrap: wrap;
    gap: 8px;
    padding: 14px 12px;
    padding-top: calc(14px + var(--safe-top));
    background: rgba(255, 255, 255, 0.03);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    flex-shrink: 0;
    z-index: 10;
}

.stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    min-width: 60px;
}

.stat-label {
    font-size: 0.68rem;
    color: #888;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

.stat-value {
    font-size: 1.3rem;
    font-weight: 700;
    color: #fff;
    font-variant-numeric: tabular-nums;
    font-family: 'SF Mono', 'Menlo', 'Courier New', monospace;
}

.stat-value.time {
    font-size: 1.5rem;
    letter-spacing: 1px;
}

.stat-adjust {
    display: flex;
    align-items: center;
    gap: 10px;
}

.adj-btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: 2px solid rgba(255, 255, 255, 0.3);
    background: rgba(255, 255, 255, 0.06);
    color: #fff;
    font-size: 1.2rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
    font-weight: 700;
    line-height: 1;
}

.adj-btn:active {
    background: rgba(255, 255, 255, 0.22);
    border-color: #fff;
    transform: scale(0.9);
}

.adj-val {
    font-size: 1.4rem;
    font-weight: 700;
    min-width: 36px;
    text-align: center;
    color: #fff;
}

.anim-area {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
    min-height: 0;
}

.btn-bar {
    display: flex;
    gap: 12px;
    padding: 14px 16px;
    padding-bottom: calc(14px + var(--safe-bottom));
    flex-shrink: 0;
    justify-content: center;
    background: rgba(255, 255, 255, 0.02);
    border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.btn {
    padding: 14px 28px;
    border-radius: 30px;
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    cursor: pointer;
    border: none;
    transition: all 0.2s;
    color: #fff;
    flex: 1;
    max-width: 160px;
    text-align: center;
}

.btn:active {
    transform: scale(0.94);
    opacity: 0.8;
}

.btn-pause {
    background: rgba(255, 180, 40, 0.85);
    color: #1a1a1a;
}

.btn-pause.paused {
    background: rgba(100, 200, 120, 0.85);
}

.btn-end {
    background: rgba(255, 70, 70, 0.75);
}

/* 划船机页面 */
.rowing-page {
    background: linear-gradient(180deg, #0d1a24 0%, #0f1f2e 50%, #0a141c 100%);
}

.rowing-page .stats-bar {
    background: rgba(30, 80, 120, 0.2);
    border-bottom-color: rgba(64, 180, 220, 0.2);
}

.rowing-page .stat-value {
    color: #7dd8f8;
}

.rowing-canvas {
    width: 100%;
    height: 100%;
    display: block;
}

/* 跑步/快走页面 */
.running-page {
    background: linear-gradient(180deg, #1a1008 0%, #1f140c 50%, #140c06 100%);
}

.running-page .stats-bar {
    background: rgba(180, 80, 20, 0.2);
    border-bottom-color: rgba(255, 140, 60, 0.2);
}

.running-page .stat-value {
    color: #ffb07a;
}

.walking-page {
    background: linear-gradient(180deg, #081a10 0%, #0c1f14 50%, #06140a 100%);
}

.walking-page .stats-bar {
    background: rgba(30, 130, 60, 0.2);
    border-bottom-color: rgba(100, 210, 130, 0.2);
}

.walking-page .stat-value {
    color: #7edca0;
}

.cadence-area {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 30px;
    width: 100%;
    height: 100%;
}

.foot-indicator {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    transition: transform 0.08s linear;
    will-change: transform;
}

.running-page .foot-indicator {
    background: radial-gradient(circle at 40% 35%, #ffb07a, #d4501a);
    box-shadow: 0 0 30px rgba(255, 120, 40, 0.5);
}

.walking-page .foot-indicator {
    background: radial-gradient(circle at 40% 35%, #7edca0, #1a7a3a);
    box-shadow: 0 0 30px rgba(80, 200, 120, 0.5);
}

.foot-label {
    position: absolute;
    font-size: 0.7rem;
    color: #aaa;
    bottom: -22px;
    left: 50%;
    transform: translateX(-50%);
    white-space: nowrap;
}

.foot-wrapper {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
}

/* 结束弹窗 */
.end-modal-overlay {
    position: fixed;
    inset: 0;
    z-index: 200;
    background: rgba(0, 0, 0, 0.75);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    backdrop-filter: blur(4px);
}

.end-modal {
    background: #1a1a2a;
    border-radius: 20px;
    padding: 28px 22px;
    width: 100%;
    max-width: 360px;
    color: #fff;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.end-modal h3 {
    text-align: center;
    font-size: 1.3rem;
    margin-bottom: 6px;
    font-weight: 700;
}

.modal-subtitle {
    text-align: center;
    font-size: 0.8rem;
    color: #888;
    margin-bottom: 20px;
}

.summary-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    font-size: 0.9rem;
}

.summary-row .val {
    font-weight: 600;
    color: #ddd;
}

.input-group {
    margin-top: 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.input-group label {
    font-size: 0.85rem;
    color: #bbb;
    font-weight: 500;
}

.input-group input {
    width: 100%;
    padding: 12px 14px;
    border-radius: 12px;
    border: 2px solid rgba(255, 255, 255, 0.2);
    background: rgba(255, 255, 255, 0.05);
    color: #fff;
    font-size: 1.1rem;
    font-weight: 600;
    outline: none;
    transition: border-color 0.2s;
    font-family: inherit;
}

.input-group input:focus {
    border-color: #7dd8f8;
}

.modal-btns {
    display: flex;
    gap: 12px;
    margin-top: 20px;
}

.modal-btns .btn {
    flex: 1;
    max-width: none;
    padding: 13px;
    font-size: 0.95rem;
    border-radius: 25px;
}

.btn-cancel {
    background: rgba(255, 255, 255, 0.1);
    color: #ccc;
}

.btn-confirm {
    background: rgba(64, 180, 220, 0.8);
    color: #fff;
    font-weight: 700;
}

/* 旋转提示 */
.rotate-hint {
    position: fixed;
    inset: 0;
    z-index: 300;
    background: rgba(0, 0, 0, 0.92);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 16px;
    color: #fff;
    font-size: 1rem;
    text-align: center;
    padding: 20px;
}

.rotate-icon {
    font-size: 3.5rem;
    animation: rotateHint 2s ease-in-out infinite;
}

@keyframes rotateHint {

    0%,
    100% {
        transform: rotate(0deg);
    }

    50% {
        transform: rotate(90deg);
    }
}

@media (max-width: 380px) {
    .sport-card {
        padding: 16px 14px;
        gap: 10px;
    }

    .icon-circle {
        width: 40px;
        height: 40px;
        font-size: 1.2rem;
    }

    .card-info h3 {
        font-size: 1rem;
    }

    .stat-value {
        font-size: 1.1rem;
    }

    .stat-value.time {
        font-size: 1.2rem;
    }

    .adj-btn {
        width: 30px;
        height: 30px;
        font-size: 1rem;
    }

    .adj-val {
        font-size: 1.1rem;
    }

    .btn {
        padding: 12px 18px;
        font-size: 0.9rem;
    }

    .foot-indicator {
        width: 38px;
        height: 38px;
    }

    .cadence-area {
        gap: 20px;
    }
}

@media (min-width: 420px) {
    .foot-indicator {
        width: 60px;
        height: 60px;
    }

    .cadence-area {
        gap: 40px;
    }
}
</style>
