<template>
  <TodoSubmit @logo="gotoHome"></TodoSubmit>
  <div class="container">
    <MessageBox :title="title" :message="content"></MessageBox>
    <Footer :is-admin="false" :config='[]'></Footer>
  </div>
</template>

<script setup lang="ts">
import router from '@/router'
import { ref, onMounted } from 'vue'
import axios from 'axios'

import TodoSubmit from '@/components/submit/TodoSubmit.vue'
import MessageBox from '@/components/MessageBox.vue'
import Footer from '@/components/footer/TodoFooter.vue'

// ========================================================== TodoSubmit 相关配置 ==========================================================
function gotoHome() {
  document.title = '代办事项列表'
  router.push({ path: '/todo' })
}

// ========================================================== MessageBox 相关配置 ==========================================================
let title = ref('数据')
let content = ref('')

onMounted(() => {
  const type = router.currentRoute.value.params.type as string
  switch (type) {
    case 'log':
      return loadSysLog()
    case 'report':
      return loadWeeklyReport()
    default:
      console.warn('无效的类型')
  }
  document.title = title.value
  axios.get('/log/' + type).then((rep) => (content.value = rep.data))
})


function loadSysLog() {
  title.value = '系统日志'
  document.title = title.value
  axios.get('/log/log').then((rep) => (content.value = rep.data))
}

function loadWeeklyReport() {
  title.value = '日报汇总'
  document.title = title.value
  axios.get('/summary/getWeeklySummary').then((rep) => (content.value = rep.data))
}


</script>

<style scoped>
.container {
  max-width: 1000px;
  padding: 0 10px;
  margin: 0 auto;
}
</style>
