<template>
  <div class="container">
    <h2>{{ title }}</h2>
    <MessageBox :message="content"></MessageBox>
  </div>
</template>

<script setup lang="ts">
import router from '@/router'
import { ref, onMounted } from 'vue'
import axios from 'axios'

import MessageBox from '@/components/MessageBox.vue'

let title = '数据'
let content = ref('')

onMounted(() => {
  const type = router.currentRoute.value.params.type as string
  switch (type) {
    case 'log':
      title = '系统日志'
      break
    default:
      console.warn('无效的类型')
  }
  document.title = title
  axios.get('/log/' + type).then((rep) => (content.value = rep.data))
})
</script>

<style scoped>
.container {
  max-width: 1000px;
  padding: 0 10px;
  margin: 0 auto;
}
</style>
