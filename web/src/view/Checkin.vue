<template>
  <div class="checkin-record-page">
    <!-- Toast -->
    <Transition name="toast-fade">
      <div v-if="toast.show" :class="['toast', toast.type]">
        {{ toast.message }}
      </div>
    </Transition>

    <!-- 成就弹窗 -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div
          v-if="showAchievementModal"
          class="achievement-overlay"
          @click.self="closeAchievementModal"
        >
          <div class="achievement-modal">
            <div class="ach-icon">🎉</div>
            <h3>太棒了！获得新成就</h3>
            <ul class="ach-list">
              <li v-for="ach in newAchievements" :key="ach.name">
                <span class="ach-emoji">{{ ach.icon || '🏆' }}</span>
                <span>
                  <strong>{{ ach.name }}</strong>
                  <br />
                  <small>{{ ach.description }}</small>
                </span>
              </li>
            </ul>
            <button class="btn-close-ach" @click="closeAchievementModal">
              我知道了
            </button>
          </div>
        </div>
      </Transition>

      <!-- 补卡确认弹窗 -->
      <Transition name="modal-fade">
        <div
          v-if="showMakeupConfirm"
          class="confirm-overlay"
          @click.self="cancelMakeup"
        >
          <div class="confirm-modal">
            <p>
              📋 确认对 <strong>{{ makeupTargetDay }}</strong> 进行补卡吗？<br />
              <small>剩余补卡次数：{{ statData.remaining_make_up }}</small>
            </p>
            <div class="confirm-btns">
              <button class="btn btn-cancel" @click="cancelMakeup">取消</button>
              <button class="btn btn-confirm" @click="confirmMakeup">
                确认补卡
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 1. 项目选择区 -->
    <section class="card project-selector">
      <div
        v-for="(info, itemName) in allItemsData"
        :key="itemName"
        :class="['project-chip', { active: currentItemName === itemName }]"
        @click="switchProject(itemName as string)"
      >
        <span class="emoji">{{ (info as ProjectInfo).emoji || '📌' }}</span>
        <span>{{ itemName }}</span>
      </div>
    </section>

    <!-- 2. 进度条 -->
    <section class="card progress-section">
      <div class="progress-label">
        <span>当前周期打卡进度</span>
        <strong>{{ currentProjectProcess }} / 21 天</strong>
      </div>
      <div class="progress-bar-outer">
        <div
          class="progress-bar-inner"
          :style="{ width: progressPercent + '%' }"
        ></div>
      </div>
    </section>

    <!-- 3. 日历模块 -->
    <section class="card calendar-section">
      <div class="calendar-header">
        <button class="nav-btn" @click="prevMonth" title="上个月">◀</button>
        <span class="month-title">{{ calendarDisplayTitle }}</span>
        <button class="nav-btn" @click="nextMonth" title="下个月">▶</button>
      </div>
      <div class="calendar-weekdays">
        <span v-for="wd in weekDayLabels" :key="wd">{{ wd }}</span>
      </div>
      <div class="calendar-grid">
        <div
          v-for="(cell, idx) in calendarCells"
          :key="idx"
          :class="getCellClass(cell)"
          :title="cell.tooltip || ''"
          @click="handleCellClick(cell)"
        >
          {{ cell.displayDay }}
        </div>
      </div>
      <div class="calendar-legend">
        <span><span class="legend-dot green"></span> 已打卡</span>
        <span><span class="legend-dot red"></span> 错过打卡</span>
        <span><span class="legend-dot gray"></span> 还没到 / 今天未打卡</span>
        <span><span class="legend-dot blue-ring"></span> 今天</span>
      </div>
    </section>

    <!-- 4. 统计面板 -->
    <section class="card stats-panel">
      <div class="stat-item">
        <div class="stat-value">{{ statData.total_count }}</div>
        <div class="stat-label">总打卡天数</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">{{ statData.continuous_count }}</div>
        <div class="stat-label">连续打卡天数</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">{{ statData.achievement_count }}</div>
        <div class="stat-label">获得成就数量</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">{{ statData.remaining_make_up }}</div>
        <div class="stat-label">剩余补卡次数</div>
      </div>
    </section>

    <!-- 5. 时间段分布 -->
    <section class="card time-dist-section">
      <div class="time-dist-title">📊 本月打卡时间段分布（小时级别）</div>
      <div
        v-if="timeDistribution.segments.length === 0"
        class="time-dist-empty"
      >
        暂无打卡数据
      </div>
      <div v-else>
        <div class="time-dist-container">
          <div
            v-for="(seg, idx) in timeDistribution.segments"
            :key="idx"
            class="time-block"
            :style="getTimeBlockStyle(seg, timeDistribution.maxCount)"
            :title="seg.label + ' — ' + seg.count + '次打卡'"
          >
            <span class="time-block-tooltip">{{ seg.label }}<br />{{ seg.count }}次</span>
          </div>
        </div>
        <div class="time-dist-labels">
          <span>{{ timeDistribution.segments[0]?.label?.split('-')[0] || '' }}</span>
          <span class="granularity-hint">粒度：{{ timeDistribution.granularityLabel }}</span>
          <span>{{
            timeDistribution.segments[timeDistribution.segments.length - 1]?.label?.split('-')[1] || ''
          }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import axios from 'axios';

// ==================== 类型定义 ====================
interface Achievement {
  name: string;
  description: string;
  icon?: string;
}

interface ProjectInfo {
  record: string[];
  emoji: string;
  new_achievements?: Achievement[];
}

interface StatData {
  total_count: number;
  continuous_count: number;
  achievement_count: number;
  remaining_make_up: number;
  process: number;
}

interface CalendarCell {
  displayDay: number;
  dateStr: string;
  status: 'done' | 'missed' | 'future' | 'padding';
  isToday: boolean;
  inMonth: boolean;
  tooltip: string;
}

interface TimeSegment {
  label: string;
  count: number;
}

// ==================== 响应式状态 ====================
const allItemsData = ref<Record<string, ProjectInfo>>({});
const currentItemName = ref<string>('');
const currentMonth = ref<string>(''); // 'YYYY-MM'
const currentDisplayRecords = ref<string[]>([]);

const statData = ref<StatData>({
  total_count: 0,
  continuous_count: 0,
  achievement_count: 0,
  remaining_make_up: 0,
  process: 0,
});

const showAchievementModal = ref<boolean>(false);
const newAchievements = ref<Achievement[]>([]);
const showMakeupConfirm = ref<boolean>(false);
const makeupTargetDay = ref<string>('');
const toast = reactive({ show: false, message: '', type: 'success' });

const weekDayLabels = ['日', '一', '二', '三', '四', '五', '六'];

// ==================== 计算属性 ====================
const currentProjectProcess = computed<number>(() => {
  return statData.value.process
});

const progressPercent = computed<number>(() => {
  return Math.round(Math.min(currentProjectProcess.value, 21) / 21 * 100);
});

const calendarDisplayTitle = computed<string>(() => {
  if (!currentMonth.value) return '';
  const [year, month] = currentMonth.value.split('-');
  return `${year}年 ${parseInt(month)}月`;
});

const todayDateStr = computed<string>(() => {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
});

const calendarCells = computed<CalendarCell[]>(() => {
  if (!currentMonth.value) return [];
  const [yearStr, monthStr] = currentMonth.value.split('-');
  const year = parseInt(yearStr);
  const month = parseInt(monthStr);
  const firstDay = new Date(year, month - 1, 1);
  const startDayOfWeek = firstDay.getDay();
  const daysInMonth = new Date(year, month, 0).getDate();

  const recordDateSet = new Set<string>();
  currentDisplayRecords.value.forEach((ts) => {
    recordDateSet.add(ts.split(' ')[0]);
  });

  const cells: CalendarCell[] = [];

  // 上月填充
  if (startDayOfWeek > 0) {
    const prevMonthDays = new Date(year, month - 1, 0).getDate();
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      const d = prevMonthDays - i;
      const dateStr = formatDateStr(year, month - 1, d);
      cells.push({
        displayDay: d,
        dateStr,
        status: 'padding',
        isToday: dateStr === todayDateStr.value,
        inMonth: false,
        tooltip: '',
      });
    }
  }

  // 本月
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = formatDateStr(year, month, d);
    const isDone = recordDateSet.has(dateStr);
    const isToday = dateStr === todayDateStr.value;
    const isFutureDate = dateStr > todayDateStr.value;
    const isPast = dateStr < todayDateStr.value;

    let status: CalendarCell['status'];
    if (isDone) {
      status = 'done';
    } else if (isToday) {
      status = 'future';
    } else if (isPast) {
      status = 'missed';
    } else {
      status = 'future';
    }

    let tooltip = '';
    if (isDone) tooltip = '✅ 已打卡';
    else if (status === 'missed') tooltip = '❌ 错过打卡（点击可补卡）';
    else if (isToday) tooltip = '⏳ 今天还未打卡';
    else if (status === 'future') tooltip = '📅 还没到';

    cells.push({
      displayDay: d,
      dateStr,
      status,
      isToday,
      inMonth: true,
      tooltip,
    });
  }

  // 下月填充
  const remaining = (7 - (cells.length % 7)) % 7;
  for (let d = 1; d <= remaining; d++) {
    const dateStr = formatDateStr(year, month + 1, d);
    cells.push({
      displayDay: d,
      dateStr,
      status: 'padding',
      isToday: dateStr === todayDateStr.value,
      inMonth: false,
      tooltip: '',
    });
  }

  return cells;
});

const timeDistribution = computed<{
  segments: TimeSegment[];
  maxCount: number;
  granularityLabel: string;
}>(() => {
  const records = currentDisplayRecords.value;
  if (!records.length) {
    return { segments: [], maxCount: 0, granularityLabel: '' };
  }

  const minutesArr = records.map((ts) => {
    const [h, m] = ts.split(' ')[1].split(':').map(Number);
    return h * 60 + m;
  });

  const minMinute = Math.min(...minutesArr);
  const maxMinute = Math.max(...minutesArr);
  const span = maxMinute - minMinute;

  let segmentMinutes: number;
  let granularityLabel: string;
  if (span <= 360) {
    segmentMinutes = 30;
    granularityLabel = '半小时';
  } else if (span <= 840) {
    segmentMinutes = 60;
    granularityLabel = '1小时';
  } else {
    segmentMinutes = 120;
    granularityLabel = '2小时';
  }

  const startMinute = Math.floor(minMinute / segmentMinutes) * segmentMinutes;
  const endMinute = Math.ceil(maxMinute / segmentMinutes) * segmentMinutes;
  const totalSegments = Math.ceil((endMinute - startMinute) / segmentMinutes);

  const segments: TimeSegment[] = [];
  for (let i = 0; i < totalSegments; i++) {
    const start = startMinute + i * segmentMinutes;
    const end = start + segmentMinutes;
    const label = `${padTime(Math.floor(start / 60))}:${padTime(start % 60)}-${padTime(Math.floor(end / 60))}:${padTime(end % 60)}`;
    segments.push({ label, count: 0 });
  }

  minutesArr.forEach((m) => {
    const idx = Math.floor((m - startMinute) / segmentMinutes);
    if (idx >= 0 && idx < segments.length) {
      segments[idx].count++;
    }
  });

  const maxCount = Math.max(...segments.map((s) => s.count), 1);
  return { segments, maxCount, granularityLabel };
});

// ==================== 工具函数 ====================
function formatDateStr(year: number, month: number, day: number): string {
  const date = new Date(year, month - 1, day);
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function padTime(n: number): string {
  return String(n).padStart(2, '0');
}

function showToastMsg(message: string, type: 'success' | 'error' = 'success') {
  toast.show = true;
  toast.message = message;
  toast.type = type;
  setTimeout(() => {
    toast.show = false;
  }, 2200);
}

// ==================== 交互与样式辅助 ====================
function getCellClass(cell: CalendarCell) {
  return {
    'calendar-cell': true,
    'in-month': cell.inMonth,
    done: cell.status === 'done',
    missed: cell.status === 'missed',
    future: cell.status === 'future' || cell.status === 'padding',
    'today-ring': cell.isToday && cell.inMonth,
  };
}

function handleCellClick(cell: CalendarCell): void {
  if (!cell.inMonth) return;
  if (cell.status === 'missed' && !cell.isToday) {
    if (statData.value.remaining_make_up > 0) {
      makeupTargetDay.value = cell.dateStr;
      showMakeupConfirm.value = true;
    } else {
      showToastMsg('补卡次数已用完，无法补卡', 'error');
    }
  } else if (cell.isToday && cell.status === 'future') {
    showToastMsg('今天还未结束，请及时打卡哦~', 'error');
  }
}

function getTimeBlockStyle(seg: TimeSegment, maxCount: number) {
  const ratio = maxCount > 0 ? seg.count / maxCount : 0;
  const r = Math.round(232 - ratio * 140);
  const g = Math.round(245 - ratio * 120);
  const b = Math.round(233 - ratio * 180);
  const height = 28 + ratio * 28;
  return {
    backgroundColor: `rgb(${r},${g},${b})`,
    height: height + 'px',
    width: '100%',
    maxWidth: '48px',
    flex: '1 0 auto',
    borderRadius: '5px',
  };
}

// ==================== 弹窗控制 ====================
function cancelMakeup(): void {
  showMakeupConfirm.value = false;
  makeupTargetDay.value = '';
}

function closeAchievementModal(): void {
  showAchievementModal.value = false;
  newAchievements.value = [];
}

// ==================== 数据请求 ====================
async function fetchMonthRecord(itemName: string, month: string): Promise<void> {
  try {
    const res = await axios.post('/checkin/month_record', {
      item_name: itemName,
      month,
    });
    currentDisplayRecords.value = Array.isArray(res.data)
      ? res.data
      : res.data?.record ?? [];
  } catch (err) {
    console.error('获取月份记录失败:', err);
    currentDisplayRecords.value = [];
  }
}

async function fetchStatData(itemName: string): Promise<void> {
  try {
    const res = await axios.post('/checkin/stat', {
      item_name: itemName,
    });
    if (res.data) {
      statData.value = {
        total_count: res.data.total_count ?? 0,
        continuous_count: res.data.continuous_count ?? 0,
        achievement_count: res.data.achievement_count ?? 0,
        remaining_make_up: res.data.remaining_make_up ?? 0,
        process: res.data.process ?? 0,
      };
    }
  } catch (err) {
    console.error('获取统计数据失败:', err);
  }
}

async function refreshAllItemsData(): Promise<void> {
  try {
    const res = await axios.post('/api/checkin/record');
    if (res.data) {
      allItemsData.value = res.data;
      const info = allItemsData.value[currentItemName.value];
      if (info && currentMonth.value === getNowMonth()) {
        currentDisplayRecords.value = info.record || [];
      }
    }
  } catch (err) {
    console.error('刷新项目数据失败:', err);
  }
}

function getNowMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

async function switchProject(itemName: string): Promise<void> {
  if (currentItemName.value === itemName) return;
  currentItemName.value = itemName;
  if (currentMonth.value === getNowMonth()) {
    const info = allItemsData.value[itemName];
    if (info) currentDisplayRecords.value = info.record || [];
  } else {
    await fetchMonthRecord(itemName, currentMonth.value);
  }
  await fetchStatData(itemName);
}

async function prevMonth(): Promise<void> {
  const [y, m] = currentMonth.value.split('-').map(Number);
  let newY = y, newM = m - 1;
  if (newM < 1) { newM = 12; newY--; }
  currentMonth.value = `${newY}-${String(newM).padStart(2, '0')}`;
  await onMonthChanged();
}

async function nextMonth(): Promise<void> {
  const [y, m] = currentMonth.value.split('-').map(Number);
  let newY = y, newM = m + 1;
  if (newM > 12) { newM = 1; newY++; }
  currentMonth.value = `${newY}-${String(newM).padStart(2, '0')}`;
  await onMonthChanged();
}

async function onMonthChanged(): Promise<void> {
  if (!currentItemName.value) return;
  if (currentMonth.value === getNowMonth()) {
    const info = allItemsData.value[currentItemName.value];
    if (info) currentDisplayRecords.value = info.record || [];
  } else {
    await fetchMonthRecord(currentItemName.value, currentMonth.value);
  }
}

async function confirmMakeup(): Promise<void> {
  if (!makeupTargetDay.value || !currentItemName.value) return;
  showMakeupConfirm.value = false;
  try {
    const res = await axios.post('/checkin/makeup', {
      item_name: currentItemName.value,
      day: makeupTargetDay.value,
    });
    if (res.data === true || res.data?.success === true) {
      showToastMsg('补卡成功！');
      await fetchMonthRecord(currentItemName.value, currentMonth.value);
      await fetchStatData(currentItemName.value);
      await refreshAllItemsData();
    } else {
      showToastMsg('补卡失败，请重试', 'error');
    }
  } catch (err) {
    console.error('补卡请求失败:', err);
    showToastMsg('网络错误，补卡失败', 'error');
  } finally {
    makeupTargetDay.value = '';
  }
}

// ==================== 初始化 ====================
onMounted(async () => {
  try {
    const res = await axios.post('/checkin/record');
    if (res.data) {
      allItemsData.value = res.data;
      const names = Object.keys(res.data);
      if (names.length > 0) {
        currentItemName.value = names[0];
        currentMonth.value = getNowMonth();
        const firstInfo = res.data[names[0]];
        currentDisplayRecords.value = firstInfo.record || [];

        if (firstInfo.new_achievements?.length) {
          newAchievements.value = firstInfo.new_achievements;
          showAchievementModal.value = true;
        }
        await fetchStatData(names[0]);
      }
    }
  } catch (err) {
    console.error('初始化失败:', err);
    showToastMsg('数据加载失败，请刷新重试', 'error');
  }
});
</script>

<style scoped>
/* ========== 全局变量与重置 ========== */
.checkin-record-page {
  --green-done: #4caf84;
  --red-missed: #e57373;
  --gray-future: #e2e8f0;
  --blue-today: #3b82f6;
  --bg-card: #ffffff;
  --bg-page: #f8fafb;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --border: #e8ecf1;
  --radius-sm: 8px;
  --radius-md: 14px;
  --radius-lg: 20px;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
  --shadow-md: 0 4px 16px rgba(0,0,0,0.08);
  --transition: 0.2s ease;

  font-family: 'PingFang SC', 'Noto Sans SC', 'Helvetica Neue', system-ui, sans-serif;
  color: var(--text-primary);
  padding: 16px;
  max-width: 640px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 卡片容器 */
.card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 20px 18px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border);
}

/* ---------- 项目选择器 ---------- */
.project-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 14px 16px;
}
.project-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 24px;
  background: #f1f5f9;
  color: var(--text-secondary);
  font-size: 0.9rem;
  font-weight: 500;
  border: 2px solid transparent;
  cursor: pointer;
  transition: var(--transition);
  user-select: none;
}
.project-chip:hover {
  background: #eef2f7;
}
.project-chip.active {
  background: #ecfdf5;
  border-color: var(--green-done);
  color: #1b5e3e;
  font-weight: 600;
}
.project-chip .emoji {
  font-size: 1.2rem;
}

/* ---------- 进度条 ---------- */
.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  margin-bottom: 8px;
}
.progress-bar-outer {
  height: 8px;
  border-radius: 8px;
  background: #e8ecf1;
  overflow: hidden;
}
.progress-bar-inner {
  height: 100%;
  border-radius: 8px;
  background: linear-gradient(135deg, #4caf84, #34d399);
  transition: width 0.5s ease;
}

/* ---------- 日历 ---------- */
.calendar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.month-title {
  font-size: 1.1rem;
  font-weight: 700;
}
.nav-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: #fff;
  cursor: pointer;
  font-size: 1rem;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition);
}
.nav-btn:hover {
  background: #f1f5f9;
}

.calendar-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.calendar-cell {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: default;
  transition: var(--transition);
  color: #b0b8c1;
}
.calendar-cell.in-month {
  color: var(--text-primary);
}
.calendar-cell.done {
  background: #e8f5e9;
  color: #1b5e3e;
  font-weight: 600;
}
.calendar-cell.missed {
  background: #ffebee;
  color: #c62828;
  font-weight: 600;
  cursor: pointer;
}
.calendar-cell.missed:hover {
  background: #ffcdd2;
}
.calendar-cell.future {
  background: transparent;
  color: #b0b8c1;
}
/* 今天特殊边框 */
.calendar-cell.today-ring {
  box-shadow: inset 0 0 0 2.5px var(--blue-today), 0 0 0 3px rgba(59,130,246,0.18);
  border-radius: 8px;
}
.calendar-cell.today-ring.done {
  box-shadow: inset 0 0 0 2.5px var(--blue-today), 0 0 0 3px rgba(59,130,246,0.18);
  background: #e8f5e9;
}
.calendar-cell.today-ring.future {
  background: #f1f5f9; /* 今天未打卡显示浅灰色，区别于纯未来日期 */
  box-shadow: inset 0 0 0 2.5px var(--blue-today), 0 0 0 3px rgba(59,130,246,0.18);
}

.calendar-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
  font-size: 0.75rem;
  color: var(--text-secondary);
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  display: inline-block;
  margin-right: 4px;
  vertical-align: middle;
}
.legend-dot.green { background: var(--green-done); }
.legend-dot.red { background: var(--red-missed); }
.legend-dot.gray { background: var(--gray-future); }
.legend-dot.blue-ring {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  border: 2px solid var(--blue-today);
  background: #fff;
  display: inline-block;
  box-shadow: 0 0 0 2px rgba(59,130,246,0.2);
}

/* ---------- 统计面板 ---------- */
.stats-panel {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.stat-item {
  background: #f9fafb;
  border-radius: var(--radius-md);
  padding: 14px 8px;
  text-align: center;
  border: 1px solid #eef1f5;
}
.stat-value {
  font-size: 1.6rem;
  font-weight: 700;
}
.stat-label {
  font-size: 0.78rem;
  color: var(--text-secondary);
}

/* ---------- 时间段分布图 ---------- */
.time-dist-section {
  padding: 16px 14px;
}
.time-dist-title {
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 12px;
}
.time-dist-container {
  display: flex;
  gap: 3px;
  align-items: flex-end;
  flex-wrap: wrap;
  min-height: 48px;
}
.time-block {
  position: relative;
  transition: transform 0.15s;
  cursor: default;
}
.time-block:hover {
  transform: scaleY(1.12);
  z-index: 2;
  filter: brightness(1.05);
}
.time-block-tooltip {
  display: none;
  position: absolute;
  bottom: 110%;
  left: 50%;
  transform: translateX(-50%);
  background: #1e293b;
  color: #fff;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.7rem;
  white-space: nowrap;
  pointer-events: none;
}
.time-block:hover .time-block-tooltip {
  display: block;
}
.time-dist-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.68rem;
  color: #94a3b8;
  margin-top: 6px;
}
.time-dist-empty {
  color: var(--text-secondary);
  font-style: italic;
  text-align: center;
  padding: 20px;
}
.granularity-hint {
  font-size: 0.65rem;
  color: #94a3b8;
}

/* ---------- 弹窗与Toast ---------- */
.toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2000;
  padding: 10px 24px;
  border-radius: 24px;
  font-weight: 600;
  color: #fff;
  box-shadow: var(--shadow-md);
  pointer-events: none;
}
.toast.success { background: #4caf84; }
.toast.error { background: #e57373; }

.achievement-overlay,
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15,23,42,0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.achievement-modal,
.confirm-modal {
  background: #fff;
  border-radius: var(--radius-lg);
  padding: 24px;
  max-width: 380px;
  width: 100%;
  box-shadow: 0 12px 32px rgba(0,0,0,0.2);
  text-align: center;
}
.ach-list {
  list-style: none;
  padding: 0;
  margin: 16px 0;
  text-align: left;
}
.ach-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #fefce8;
  border-radius: 8px;
  margin-bottom: 6px;
}
.btn-close-ach,
.confirm-btns .btn {
  padding: 10px 24px;
  border-radius: 24px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition);
}
.btn-close-ach {
  background: var(--green-done);
  color: #fff;
}
.btn-cancel {
  background: #f1f5f9;
  color: var(--text-secondary);
}
.btn-confirm {
  background: var(--blue-today);
  color: #fff;
}

/* 过渡动画 */
.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.3s ease;
}
.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

/* ---------- 响应式调整 ---------- */
@media (max-width: 480px) {
  .checkin-record-page {
    padding: 12px;
    gap: 12px;
  }
  .card {
    padding: 16px 12px;
  }
  .calendar-cell {
    font-size: 0.75rem;
  }
  .project-chip {
    padding: 6px 12px;
    font-size: 0.8rem;
  }
  .stats-panel {
    gap: 6px;
  }
}

@media (min-width: 768px) {
  .checkin-record-page {
    max-width: 720px;
    gap: 20px;
  }
  .calendar-grid {
    gap: 6px;
  }
  .calendar-cell {
    font-size: 0.95rem;
  }
}
</style>