<template>
  <div class="container">
    <!-- 任务切换栏 -->
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab"
        :class="{ active: activeTab === tab }"
        @click="activeTab = tab"
      >
        {{ taskData[tab].icon }} {{ taskData[tab].name }}
      </button>
    </div>

    <!-- 核心数据区 -->
    <div class="data-panel">
      <!-- 进度条 -->
      <div class="progress">
        <div class="progress-bar">
          <div
            class="progress-inner"
            :style="{ width: (currentTask.currentStreak / currentTask.target) * 100 + '%' }"
          >
            {{ currentTask.currentStreak }}/{{ currentTask.target }} 天
          </div>
        </div>
      </div>

      <!-- 奖励提示 -->
      <div class="reward-card">
        <div class="reward-icon">🎯</div>
        <div class="reward-content">
          <h3>即将达成奖励</h3>
          <p>{{ currentTask.rewardTip }}</p>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{{ currentTask.monthCompletion }}%</div>
          <div class="stat-label">本月完成率</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ currentTask.totalDays }}</div>
          <div class="stat-label">总打卡天数</div>
        </div>
      </div>

      <!-- 日历 -->
      <div class="calendar">
        <div class="weekdays">
          <div v-for="day in ['日', '一', '二', '三', '四', '五', '六']" :key="day">{{ day }}</div>
        </div>
        <div class="days-grid">
          <div
            v-for="date in calendarDates"
            :key="date"
            :class="{ 'has-record': isDateChecked(date) }"
            @click="showDateDetail(date)"
          >
            {{ date }}
          </div>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="actions">
      <button @click="handleMakeup">补打卡 ({{ makeupChances }}次剩余)</button>
      <button @click="handleShare">分享成就</button>
      <button @click="handleRemind">设置提醒</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'

interface Task {
  icon: string
  name: string
  currentStreak: number
  target: number
  rewardTip: string
  monthCompletion: number
  totalDays: number
  checkedDates: number[]
}

interface TaskData {
  [key: string]: Task
}

// 静态数据
const tabs = ['words', 'sport']
const taskData = reactive<TaskData>({
  words: {
    icon: '📖',
    name: '每日背单词',
    currentStreak: 7,
    target: 30,
    rewardTip: '再坚持3天解锁周徽章',
    monthCompletion: 85,
    totalDays: 132,
    checkedDates: [1, 3, 5, 7, 8, 10, 12]
  },
  sport: {
    icon: '🏃',
    name: '每日运动',
    currentStreak: 3,
    target: 30,
    rewardTip: '连续打卡5天获得运动达人称号',
    monthCompletion: 60,
    totalDays: 45,
    checkedDates: [2, 4, 6]
  }
})

// 响应式状态
const activeTab = ref<string>('words')
const makeupChances = ref<number>(3)

// 计算属性
const currentTask = computed(() => taskData[activeTab.value])

// 日历日期生成（当前月份）
const calendarDates = computed(() => {
  const date = new Date()
  const year = date.getFullYear()
  const month = date.getMonth()

  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)

  return Array.from({ length: lastDay.getDate() }, (_, i) => i + 1)
})

// 方法
const isDateChecked = (date: number) => {
  return currentTask.value.checkedDates.includes(date)
}

const showDateDetail = (date: number) => {
  alert(`日期 ${date} 的打卡详情`)
}

const handleMakeup = () => {
  if (makeupChances.value > 0) {
    makeupChances.value--
    alert('补打卡成功！')
  } else {
    alert('本月补打卡次数已用完')
  }
}

const handleShare = () => {
  const text = `我正在坚持【${currentTask.value.name}】，已连续打卡${currentTask.value.currentStreak}天！`
  alert(`分享内容：${text}`)
}

const handleRemind = () => {
  const time = prompt('设置提醒时间（例如 20:00）')
  if (time) alert(`已设置每日提醒时间：${time}`)
}
</script>

<style scoped>
.container {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  font-family: 'Segoe UI', system-ui, sans-serif;
  color: #2c3e50;
}

.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.tabs button {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  background: #f0f0f0;
  color: #666;
  transition: all 0.2s;
  font-size: 15px;
}

.tabs .active {
  background: #007bff;
  color: white;
  box-shadow: 0 2px 6px rgba(0,123,255,0.3);
}

.progress-bar {
  height: 36px;
  background: #e9ecef;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
  margin: 24px 0;
}

.progress-inner {
  height: 100%;
  background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
  border-radius: 20px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  color: white;
  font-weight: 500;
  justify-content: flex-end;
  transition: width 0.5s ease;
}

.reward-card {
  background: #fff9eb;
  border: 2px solid #ffe082;
  border-radius: 12px;
  padding: 18px;
  margin: 24px 0;
  display: flex;
  align-items: center;
  gap: 15px;
}

.reward-icon {
  font-size: 36px;
  flex-shrink: 0;
}

.reward-content h3 {
  margin: 0 0 6px;
  color: #e67e22;
  font-size: 17px;
  font-weight: 600;
}

.reward-content p {
  margin: 0;
  color: #d35400;
  font-size: 15px;
  line-height: 1.4;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin: 24px 0;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  box-shadow: 0 3px 6px rgba(0,0,0,0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 5px 12px rgba(0,0,0,0.15);
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #007bff;
  margin-bottom: 8px;
}

.stat-label {
  color: #666;
  font-size: 14px;
  letter-spacing: 0.5px;
}

.calendar {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin: 20px 0;
}

.weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
  margin-bottom: 8px;
  color: #666;
  font-size: 14px;
  text-align: center;
}

.days-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.days-grid div {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: #f8f9fa;
  transition: all 0.2s;
  font-weight: 500;
  cursor: pointer;
}

.days-grid div:hover {
  background: #e9ecef;
}

.days-grid .has-record {
  background: #4caf50;
  color: white;
  box-shadow: 0 2px 4px rgba(76,175,80,0.3);
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 28px;
}

.actions button {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #007bff 0%, #0062cc 100%);
  color: white;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.actions button:hover {
  opacity: 0.92;
  transform: translateY(-2px);
  box-shadow: 0 3px 8px rgba(0,123,255,0.3);
}

.actions button:active {
  transform: translateY(0);
}
</style>