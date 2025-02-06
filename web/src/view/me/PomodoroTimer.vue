<template>
  <div class="pomodoro-container">
    <div class="circular-progress">
      <svg :width="size" :height="size">
        <circle
          class="progress-bg"
          :cx="size/2"
          :cy="size/2"
          :r="radius"
          :stroke-width="strokeWidth"
        />
        <circle
          class="progress-bar"
          :cx="size/2"
          :cy="size/2"
          :r="radius"
          :stroke-width="strokeWidth"
          :style="progressStyle"
          stroke-linecap="round"
        />
      </svg>
      <div class="time-display">
        <div class="task-name">{{ taskName }}</div>
        <div class="time">{{ formattedTime }}</div>
      </div>
    </div>

    <div v-if="showAlert" class="alert">
      <h2>「{{ taskName }}」时间到！🍅</h2>
      <button @click="resetTimer">确定</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'


const props = defineProps({
  taskName: {
    type: String,
    default: '当前任务'
  }
})


const WORK_DURATION = 1 * 60 // 25分钟（秒）
const size = 300              // 容器尺寸
const strokeWidth = 12        // 进度条宽度
const radius = (size - strokeWidth) / 2 - 5
const circumference = 2 * Math.PI * radius

// 响应式数据
const timeLeft = ref(WORK_DURATION)
const showAlert = ref(false)
let timer = null

// 自动开始计时
onMounted(startTimer)
onBeforeUnmount(() => clearInterval(timer))

// 进度条样式计算
const progress = computed(() =>
  1 - timeLeft.value / WORK_DURATION
)

const progressStyle = computed(() => ({
  strokeDasharray: circumference,
  strokeDashoffset: circumference * (1 - progress.value)
}))

// 格式化时间显示
const formattedTime = computed(() => {
  const minutes = Math.floor(timeLeft.value / 60)
    .toString()
    .padStart(2, '0')
  const seconds = (timeLeft.value % 60)
    .toString()
    .padStart(2, '0')
  return `${minutes}:${seconds}`
})

// 计时器控制
function startTimer() {
  timer = setInterval(() => {
    timeLeft.value--
    if (timeLeft.value <= 0) {
      clearInterval(timer)
      showAlert.value = true
    }
  }, 1000)
}

function resetTimer() {
  clearInterval(timer)
  timeLeft.value = WORK_DURATION
  showAlert.value = false
  startTimer()
}
</script>

<style scoped>

.time-display {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

.task-name {
  font-size: 1.4rem;
  color: #666;
  margin-bottom: 0.8rem;
  max-width: 80%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.time {
  font-size: 3.5rem;
  font-weight: bold;
  color: #2c3e50;
  line-height: 1;
}


.pomodoro-container {
  font-family: Arial, sans-serif;
  text-align: center;
}

.circular-progress {
  position: relative;
  margin: 20px auto;
  width: v-bind(size + 'px');
  height: v-bind(size + 'px');
}

svg {
  transform: rotate(-90deg);
}

circle.progress-bg {
  fill: none;
  stroke: #eee;
}

circle.progress-bar {
  fill: none;
  stroke: #42b983;
  transition: 0.3s stroke-dashoffset;
}

.time-display {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 3.5rem;
  font-weight: bold;
  color: #2c3e50;
}

.alert {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 0 20px rgba(0,0,0,0.1);
  text-align: center;
}

.alert button {
  padding: 0.8rem 2rem;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1.1rem;
  margin-top: 1rem;
}

.alert button:hover {
  background: #3aa876;
}
</style>