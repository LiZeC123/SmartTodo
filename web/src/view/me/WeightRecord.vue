<template>
  <TodoSubmit></TodoSubmit>
  <div class="container">
    <!-- 体重输入表单 -->
    <div class="input-section">
      <h2>记录体重</h2>
      <form @submit.prevent="addWeight">
        <div class="input-group">
          <input
            type="number"
            step="0.1"
            v-model="newWeight"
            placeholder="输入体重（kg）"
            required
          />
          <button type="submit">提交</button>
        </div>
      </form>
    </div>

    <!-- 体重趋势图表 -->
    <div class="chart-section">
      <h2>体重趋势</h2>
      <div class="chart-container">
        <canvas ref="chart"></canvas>
      </div>
    </div>

    <!-- 历史记录列表 -->
    <div class="history-section">
      <h2>历史记录</h2>
      <ul>
        <li v-for="entry in reversedHistory" :key="entry.id">
          <span class="date">{{ formatDate(entry.create_time) }}</span>
          <span class="weight">{{ entry.weight }} kg</span>
          <button @click="deleteEntry(entry.id)" class="delete-btn">×</button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ref, onMounted, type Ref, computed } from 'vue'
import { Chart } from 'chart.js/auto'
import dayjs from 'dayjs'
import TodoSubmit from '@/components/submit/TodoSubmit.vue'

interface WeightLog {
  id: number
  weight: number
  create_time: string
}


// 体重历史数据
const weightHistory: Ref<WeightLog[]>= ref([])

const newWeight = ref('')
const chart: any = ref(null)
let chartInstance: Chart|null = null

// 日期格式化
const formatDate = (dateStr: string) => {
  return dayjs(dateStr).format('MM/DD')
}

// 添加体重记录
const addWeight = () => {
  if (!newWeight.value) return

  axios.post('/me/weight/add', {'weight':newWeight.value }).then(() => {
    weightHistory.value.push({
      id: Date.now(),
      weight: parseFloat(newWeight.value),
      create_time: dayjs().format('YYYY-MM-DD')
    })
    newWeight.value = ''
    reloadChart()
  })

}

// 删除记录
const deleteEntry = (id:number) => {
  axios.post('/me/weight/remove', {'id': id}).then(() => {
    weightHistory.value = weightHistory.value.filter(entry => entry.id !== id)
    reloadChart()
  })
}

// 初始化图表
onMounted( () => {
  axios.post<WeightLog[]>('/me/weight/query', {}).then(res => {
    weightHistory.value = res.data
    chartInstance = new Chart(chart.value, {
      type: 'line',
      data: {
        labels: weightHistory.value.map(entry => formatDate(entry.create_time)),
        datasets: [{
          label: '体重变化 (kg)',
          data: weightHistory.value.map(entry => entry.weight),
          borderColor: '#42b983',
          tension: 0.4,
          fill: false
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: false
          }
        }
      }
    })
  })
})

function reloadChart() {
  if (chartInstance) {
    chartInstance.data.labels = weightHistory.value.map(entry => formatDate(entry.create_time))
    chartInstance.data.datasets[0].data = weightHistory.value.map(entry => entry.weight)
    chartInstance.update()
  }
}

// 计算属性：生成反向列表
const reversedHistory= computed(() => {
  // 通过浅拷贝避免修改原数组
  return [...weightHistory.value].reverse();
});



</script>

<style scoped>
.container {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

.input-section {
  margin-bottom: 30px;
}

.input-group {
  display: flex;
  gap: 10px;
}

input {
  flex: 1;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 16px;
}

button {
  padding: 12px 20px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
}

button:hover {
  background-color: #3aa876;
}

.chart-container {
  position: relative;
  height: 300px;
  margin: 20px 0;
}

.history-section ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.history-section li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin: 8px 0;
  background-color: #f5f5f5;
  border-radius: 8px;
}

.date {
  color: #666;
  font-size: 0.9em;
}

.weight {
  font-weight: bold;
  color: #42b983;
}

.delete-btn {
  background-color: #ff4444;
  padding: 4px 10px;
  border-radius: 50%;
}

.delete-btn:hover {
  background-color: #cc0000;
}

/* 移动端适配 */
@media (max-width: 480px) {
  .container {
    padding: 10px;
  }

  input, button {
    font-size: 14px;
    padding: 10px;
  }

  .chart-container {
    height: 250px;
  }
}
</style>