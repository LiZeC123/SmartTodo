<template>
  <TodoSubmit></TodoSubmit>
  <div class="points-container">
    <!-- 当前积分展示 -->
    <div class="current-points">
      <h2>当前积分</h2>
      <div class="points-number">{{ currentPoints }}</div>
    </div>

    <!-- 本周积分统计 -->
    <div class="weekly-stats">
      <h3>本周积分变动</h3>
      <div class="stats-grid">
        <div class="stat-item">
          <span>获取积分</span>
          <div class="stat-value positive">+{{ weeklyEarned }}</div>
        </div>
        <div class="stat-item">
          <span>消耗积分</span>
          <div class="stat-value negative">-{{ weeklyUsed }}</div>
        </div>
      </div>
    </div>

    <!-- 积分兑换模块 -->
    <div class="exchange-section">
      <h3>积分兑换</h3>
      <div class="exchange-item" v-for="item in exchangeItems" :key="item.id">
        <div class="item-info">
          <div class="item-title">{{ item.name }}</div>
          <div class="item-points">{{ item.points }}积分</div>
        </div>
        <button
          class="exchange-btn"
          :disabled="currentPoints < item.points"
          @click="handleExchange(item)"
        >
          立即兑换
        </button>
      </div>
    </div>

    <!-- 积分明细 -->
    <div class="details-section">
      <h3>积分明细</h3>
      <div class="detail-list">
        <div class="detail-item" v-for="(record, index) in pointRecords" :key="index">
          <div class="detail-left">
            <div class="detail-type">{{ record.reason }}</div>
            <div class="detail-time">{{ record.create_time }}</div>
          </div>
          <div class="detail-balance">余额: {{ record.balance }} <div :class="record.credit > 0 ? 'positive' : 'negative'"> ({{ record.credit > 0 ? '+' : '' }}{{ record.credit }})</div></div>
        </div>
      </div>
    </div>
  </div>
  <Footer :is-admin="false" :config="[]"></Footer>
</template>

<script setup lang="ts">
import { ref, onMounted, type Ref } from 'vue'
import TodoSubmit from '@/components/submit/TodoSubmit.vue'
import Footer from '@/components/footer/TodoFooter.vue'
import axios from 'axios'

interface TotalCount {
  all: number,
  earned: number,
  used: number
}

interface CreditLog {
  create_time: string
  reason: string
  credit: number
  balance: number
}

interface ExchangeItem {
  id: number
  name: string
  points: number
}

// 静态数据
const currentPoints = ref(0)
const weeklyEarned = ref(0)
const weeklyUsed = ref(0)

const exchangeItems: Ref<ExchangeItem[]> = ref([])

const pointRecords: Ref<CreditLog[]> = ref([])

// 兑换处理
const handleExchange = (item: ExchangeItem) => {
  if (currentPoints.value >= item.points) {
    axios.post('credit/exchange_item', {'item_id': item.id}).then(() => {
      reloadLog()
      reloadExchangeItems()
      reloadPoints()
    })
  }
}

function reloadLog() {
  axios.post<CreditLog[]>('credit/get_detail_list', {}).then(res => {
    pointRecords.value = res.data
  })
}

function reloadExchangeItems() {
  axios.post<ExchangeItem[]>('credit/get_exchange_list', {}).then(res => {
    exchangeItems.value = res.data
  })
}

function reloadPoints() {
  axios.post<TotalCount>('credit/get_credit', {}).then(res => {
    currentPoints.value = res.data.all
    weeklyEarned.value = res.data.earned
    weeklyUsed.value = res.data.used
  })
}

onMounted(() => {
  reloadLog()
  reloadExchangeItems()
  reloadPoints()
})
</script>

<style scoped>
.points-container {
  padding: 1rem;
  max-width: 600px;
  margin: 0 auto;
}

.current-points {
  text-align: center;
  padding: 1.5rem;
  background: #f5f5f5;
  border-radius: 12px;
  margin-bottom: 1.5rem;
}

.points-number {
  font-size: 2.5rem;
  font-weight: bold;
  color: #ff5722;
}

.weekly-stats {
  margin-bottom: 1.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.stat-item {
  background: #fff;
  padding: 1rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.exchange-section {
  margin-bottom: 1.5rem;
}

.exchange-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #fff;
  margin-bottom: 0.8rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.exchange-btn {
  background: #ff5722;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  cursor: pointer;
}

.exchange-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #fff;
  margin-bottom: 0.8rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.positive {
  color: #4caf50;
}

.negative {
  color: #f44336;
}

/* 移动端适配 */
@media (max-width: 480px) {
  .points-number {
    font-size: 2rem;
  }

  .exchange-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .exchange-btn {
    margin-top: 0.5rem;
    width: 100%;
  }
}
</style>
