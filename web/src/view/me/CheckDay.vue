<template>
  <div class="checkin-calendar">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="view-switch">
        <button :class="{ active: viewMode === 'month' }" @click="viewMode = 'month'">
          月视图
        </button>
        <button :class="{ active: viewMode === 'year' }" @click="viewMode = 'year'">
          年视图
        </button>
      </div>

      <div class="date-controls">
        <button class="icon-btn" @click="prevPeriod">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
        </button>
        <span class="current-period">{{ currentPeriodText }}</span>
        <button class="icon-btn" @click="nextPeriod">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
        </button>
        <button class="today-btn" @click="goToToday">今天</button>
      </div>
    </div>

    <!-- 月视图 -->
    <div v-if="viewMode === 'month'" class="month-view">
      <div class="weekdays">
        <span v-for="day in weekDays" :key="day">{{ day }}</span>
      </div>
      <div class="calendar-grid">
        <div
          v-for="(day, idx) in monthDays"
          :key="idx"
          class="calendar-day"
          :class="{
            'not-current-month': !day.isCurrentMonth,
            'checked-in': day.isChecked,
            'not-checked': !day.isChecked && day.isCurrentMonth,
            today: day.isToday
          }"
          @click="handleDayClick(day)"
        >
          <span class="day-number">{{ day.day }}</span>
          <span class="check-status">
            <span v-if="day.isChecked" class="checked-symbol">✓</span>
            <span v-else-if="day.isCurrentMonth" class="unchecked-symbol">✗</span>
          </span>
        </div>
      </div>
    </div>

    <!-- 年视图 -->
    <div v-else class="year-view">
      <div
        v-for="month in yearMonths"
        :key="month.monthIndex"
        class="month-card"
      >
        <div class="month-title">{{ month.monthName }}</div>
        <div class="month-days-grid">
          <div
            v-for="day in month.days"
            :key="day.dateStr"
            class="year-day"
            :class="{
              'checked-in': day.isChecked,
              'not-checked': !day.isChecked && day.isCurrentMonth,
              empty: day.isEmpty
            }"
            @click="handleYearDayClick(day)"
          >
            <span v-if="!day.isEmpty" class="year-day-number">{{ day.day }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

// 打卡记录 Map (key: YYYY-MM-DD)
const checkinRecords = ref<Map<string, boolean>>(new Map())

// 视图模式
type ViewMode = 'month' | 'year'
const viewMode = ref<ViewMode>('month')

// 当前显示的日期（月视图用）
const currentYear = ref(new Date().getFullYear())
const currentMonth = ref(new Date().getMonth()) // 0-11

// 年视图当前年份
const yearViewYear = ref(new Date().getFullYear())

// 星期标题
const weekDays = ['日', '一', '二', '三', '四', '五', '六']

// ==================== Mock 数据生成 ====================
const generateMockData = () => {
  const map = new Map<string, boolean>()
  const today = new Date()
  const startYear = today.getFullYear() - 1
  const endYear = today.getFullYear() + 1
  
  for (let year = startYear; year <= endYear; year++) {
    for (let month = 0; month < 12; month++) {
      const daysInMonth = new Date(year, month + 1, 0).getDate()
      for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(year, month, day)
        const isFuture = date > today
        const isChecked = isFuture ? false : Math.random() > 0.2
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
        map.set(dateStr, isChecked)
      }
    }
  }
  
  // 确保当前月份有一些未打卡示例
  const now = new Date()
  const currentYearMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  for (let day = 1; day <= 10; day++) {
    const dateStr = `${currentYearMonth}-${String(day).padStart(2, '0')}`
    if (map.has(dateStr)) {
      map.set(dateStr, false)
    }
  }
  
  return map
}

// 初始化 Mock 数据
const initMockData = () => {
  checkinRecords.value = generateMockData()
}

// ==================== 通用方法 ====================
// 获取打卡状态
const getCheckinStatus = (year: number, month: number, day: number): boolean => {
  const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  return checkinRecords.value.get(dateStr) || false
}

// 补卡
const makeUpCheckin = (year: number, month: number, day: number) => {
  const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  if (checkinRecords.value.get(dateStr)) {
    return false
  }
  const confirmResult = confirm(`是否补卡 ${dateStr}？`)
  if (confirmResult) {
    checkinRecords.value.set(dateStr, true)
    console.log(`补卡成功: ${dateStr}`)
    return true
  }
  return false
}

// ==================== 月视图逻辑 ====================
const monthDays = computed(() => {
  const year = currentYear.value
  const month = currentMonth.value
  const firstDayOfMonth = new Date(year, month, 1)
  const startWeekday = firstDayOfMonth.getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const prevMonthDays = new Date(year, month, 0).getDate()
  const daysArray = []
  const today = new Date()
  const todayDate = today.getDate()
  const todayMonth = today.getMonth()
  const todayYear = today.getFullYear()
  
  // 添加上月填充
  for (let i = startWeekday - 1; i >= 0; i--) {
    const day = prevMonthDays - i
    daysArray.push({
      year: month === 0 ? year - 1 : year,
      month: month === 0 ? 11 : month - 1,
      day,
      isCurrentMonth: false,
      isChecked: false,
      isToday: false,
      dateStr: `${month === 0 ? year - 1 : year}-${String((month === 0 ? 11 : month - 1) + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    })
  }
  
  // 添加当月天数
  for (let day = 1; day <= daysInMonth; day++) {
    const isChecked = getCheckinStatus(year, month, day)
    const isToday = todayYear === year && todayMonth === month && todayDate === day
    daysArray.push({
      year,
      month,
      day,
      isCurrentMonth: true,
      isChecked,
      isToday,
      dateStr: `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    })
  }
  
  // 添加下月填充至42格
  const remaining = 42 - daysArray.length
  for (let i = 1; i <= remaining; i++) {
    daysArray.push({
      year: month === 11 ? year + 1 : year,
      month: month === 11 ? 0 : month + 1,
      day: i,
      isCurrentMonth: false,
      isChecked: false,
      isToday: false,
      dateStr: `${month === 11 ? year + 1 : year}-${String((month === 11 ? 0 : month + 1) + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`
    })
  }
  
  return daysArray
})

const handleDayClick = (day: any) => {
  if (!day.isCurrentMonth) return
  if (!day.isChecked) {
    makeUpCheckin(day.year, day.month, day.day)
  }
}

// ==================== 年视图逻辑 ====================
const yearMonths = computed(() => {
  const year = yearViewYear.value
  const months = []
  const today = new Date()
  const todayYear = today.getFullYear()
  const todayMonth = today.getMonth()
  const todayDate = today.getDate()
  
  for (let month = 0; month < 12; month++) {
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const firstDayWeekday = new Date(year, month, 1).getDay()
    const monthName = `${year}年${month + 1}月`
    
    const daysArray = []
    // 前置空白
    for (let i = 0; i < firstDayWeekday; i++) {
      daysArray.push({
        isEmpty: true,
        isChecked: false,
        day: 0,
        dateStr: '',
        isCurrentMonth: false,
        year,
        month
      })
    }
    // 当月日期
    for (let day = 1; day <= daysInMonth; day++) {
      const isChecked = getCheckinStatus(year, month, day)
      const isToday = todayYear === year && todayMonth === month && todayDate === day
      daysArray.push({
        isEmpty: false,
        isChecked,
        day,
        isCurrentMonth: true,
        isToday,
        dateStr: `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
        year,
        month
      })
    }
    // 补全至42格
    const remaining = 42 - daysArray.length
    for (let i = 0; i < remaining; i++) {
      daysArray.push({
        isEmpty: true,
        isChecked: false,
        day: 0,
        dateStr: '',
        isCurrentMonth: false,
        year,
        month
      })
    }
    
    months.push({
      monthIndex: month,
      monthName,
      days: daysArray
    })
  }
  return months
})

const handleYearDayClick = (day: any) => {
  if (day.isEmpty) return
  if (!day.isChecked) {
    makeUpCheckin(day.year, day.month, day.day)
  }
}

// ==================== 日期导航 ====================
const currentPeriodText = computed(() => {
  if (viewMode.value === 'month') {
    return `${currentYear.value}年 ${currentMonth.value + 1}月`
  } else {
    return `${yearViewYear.value}年`
  }
})

const prevPeriod = () => {
  if (viewMode.value === 'month') {
    if (currentMonth.value === 0) {
      currentMonth.value = 11
      currentYear.value--
    } else {
      currentMonth.value--
    }
  } else {
    yearViewYear.value--
  }
}

const nextPeriod = () => {
  if (viewMode.value === 'month') {
    if (currentMonth.value === 11) {
      currentMonth.value = 0
      currentYear.value++
    } else {
      currentMonth.value++
    }
  } else {
    yearViewYear.value++
  }
}

const goToToday = () => {
  const today = new Date()
  if (viewMode.value === 'month') {
    currentYear.value = today.getFullYear()
    currentMonth.value = today.getMonth()
  } else {
    yearViewYear.value = today.getFullYear()
  }
}

// ==================== 生命周期 ====================
onMounted(() => {
  initMockData()
})
</script>

<style scoped>
/* 样式保持不变，只微调图标符号的样式 */
.checkin-calendar {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  background: linear-gradient(135deg, #f5f7fa 0%, #e9edf2 100%);
  min-height: 100vh;
  border-radius: 24px;
}

/* 工具栏 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 32px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(10px);
  padding: 12px 24px;
  border-radius: 60px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.view-switch {
  display: flex;
  gap: 8px;
  background: #f1f3f5;
  padding: 4px;
  border-radius: 40px;
}

.view-switch button {
  padding: 8px 20px;
  border: none;
  background: transparent;
  font-size: 0.95rem;
  font-weight: 500;
  border-radius: 32px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #495057;
}

.view-switch button.active {
  background: white;
  color: #2c7da0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.date-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.icon-btn {
  background: white;
  border: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  color: #2c3e50;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.icon-btn svg {
  width: 18px;
  height: 18px;
}

.icon-btn:hover {
  background: #e9ecef;
  transform: scale(1.05);
}

.current-period {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e3c5c;
  min-width: 140px;
  text-align: center;
}

.today-btn {
  background: #2c7da0;
  color: white;
  border: none;
  padding: 6px 16px;
  border-radius: 30px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.today-btn:hover {
  background: #1f5e7a;
}

/* 月视图样式 */
.month-view {
  background: white;
  border-radius: 28px;
  padding: 24px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  overflow-x: auto;
}

.weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  margin-bottom: 16px;
  font-weight: 600;
  color: #5f7f9e;
  font-size: 0.9rem;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
}

.calendar-day {
  aspect-ratio: 1 / 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 20px;
  background: #f8f9fa;
  transition: all 0.2s;
  cursor: pointer;
  position: relative;
  padding: 8px 4px;
}

.calendar-day.not-current-month {
  background: #f1f3f5;
  opacity: 0.5;
  cursor: default;
}

.calendar-day.checked-in {
  background: linear-gradient(135deg, #a7e0b0, #6fbf73);
  color: white;
  box-shadow: 0 2px 6px rgba(111, 191, 115, 0.3);
}

.calendar-day.not-checked {
  background: #ffe8e6;
  color: #c92a2a;
  cursor: pointer;
}

.calendar-day.today {
  border: 2px solid #2c7da0;
  box-shadow: 0 0 0 2px rgba(44, 125, 160, 0.2);
}

.day-number {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 4px;
}

.check-status {
  font-size: 1.1rem;
  line-height: 1;
}

.checked-symbol {
  color: #ffffff;
  font-weight: bold;
}

.unchecked-symbol {
  color: #c92a2a;
  font-weight: bold;
}

/* 年视图样式 */
.year-view {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
}

.month-card {
  background: white;
  border-radius: 24px;
  padding: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s, box-shadow 0.2s;
}

.month-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
}

.month-title {
  font-size: 1rem;
  font-weight: 600;
  text-align: center;
  margin-bottom: 16px;
  color: #2c7da0;
  border-bottom: 2px solid #e9ecef;
  padding-bottom: 8px;
}

.month-days-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.year-day {
  aspect-ratio: 1 / 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 500;
  background: #f1f3f5;
  cursor: pointer;
  transition: all 0.1s;
}

.year-day.empty {
  background: transparent;
  cursor: default;
}

.year-day.checked-in {
  background: #6fbf73;
  color: white;
}

.year-day.not-checked {
  background: #ffb3b3;
  color: #a61e1e;
  cursor: pointer;
}

.year-day-number {
  font-size: 0.7rem;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .checkin-calendar {
    padding: 16px;
  }
  
  .toolbar {
    flex-direction: column;
    align-items: stretch;
    border-radius: 28px;
  }
  
  .view-switch {
    align-self: center;
  }
  
  .date-controls {
    justify-content: center;
  }
  
  .calendar-grid {
    gap: 4px;
  }
  
  .day-number {
    font-size: 0.9rem;
  }
  
  .year-view {
    grid-template-columns: 1fr;
  }
  
  .month-card {
    padding: 12px;
  }
}
</style>