<template>
  <TodoSubmit></TodoSubmit>
  <div class="container">
    <!-- 美化后的 Tab 切换栏 -->
    <div class="tabs">
      <button :class="{ active: currentTab === 'log' }" @click="switchTab('log')">
        系统日志
      </button>
      <button :class="{ active: currentTab === 'event' }" @click="switchTab('event')">
        事件日志
      </button>
    </div>

    <!-- 移除 title 属性，仅显示消息内容 -->
    <MessageBox :title='""' :message="content"></MessageBox>
    <Footer :is-admin="false" :config="[]"></Footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

import TodoSubmit from '@/components/submit/TodoSubmit.vue'
import MessageBox from '@/components/MessageBox.vue'
import Footer from '@/components/footer/TodoFooter.vue'

// ========================================================== MessageBox 相关配置 ==========================================================
let content = ref('')

// 当前激活的 tab
const currentTab = ref<'log' | 'event'>('log')

// 切换 tab
function switchTab(tab: 'log' | 'event') {
  currentTab.value = tab
  if (tab === 'log') {
    loadSysLog()
  } else {
    loadEventLog()
  }
}

// 初始化默认加载系统日志
onMounted(() => {
  switchTab('log')
})

function loadSysLog() {
  document.title = '系统日志'
  axios.get('/log/log').then((rep) => (content.value = rep.data))
}

function loadEventLog() {
  document.title = '事件日志'
  axios.get('/log/event').then((rep) => (content.value = rep.data))
}
</script>

<style scoped>
.container {
  max-width: 1000px;
  padding: 0 10px;
  margin: 0 auto;
}

/* 美化后的 Tab 样式 */
.tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  background: #f7f8fa;
  padding: 6px;
  border-radius: 10px;
}

.tabs button {
  flex: 1;
  padding: 10px 20px;
  border: none;
  background: transparent;
  color: #666;
  font-size: 15px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.tabs button:hover {
  background: rgba(0, 0, 0, 0.04);
  color: #333;
}

.tabs button.active {
  background: #ffffff;
  color: #1890ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.15);
  font-weight: 600;
}
</style>