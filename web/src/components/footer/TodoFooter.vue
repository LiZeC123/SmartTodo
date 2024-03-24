<template>
  <footer class="footer">
    <div class="footer-content">
      <span>Copyright &copy; {{ new Date().getFullYear() }} LiZeC</span>
      <span><a v-for="c in showConfig" @click="c.f" :key="c.name">{{ c.name }}</a></span>
    </div>

    <!-- 上传文件的控件 -->
    <input type="file" id="file_selector" style="display: none" @change="uploadFile" />
  </footer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FooterConfig } from './types'
import { getUploadFile } from './tools'

const props = defineProps<{
  isAdmin: boolean
  config: FooterConfig[]
}>()

const emit = defineEmits<{
  (e: 'upload-file', file: File | undefined): void
}>()

let showConfig = computed(() => {
  return props.config.filter((v) => props.isAdmin || !v.needAdmin)
})

function uploadFile() {
  emit('upload-file', getUploadFile())
}
</script>

<style scoped>
.footer {
  color: #666;
  font-size: 14px;
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 10px;
}

.footer-content {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
}


.footer-content span a {
  text-decoration: none;
  color: #666;
  margin-left: 5px;
  margin-right: 5px;
}


.footer-content span {
  white-space: nowrap; /* 防止内容换行 */
  margin: 0 5px; /* 调整内容间距 */
}

/* 媒体查询 */
@media screen and (max-width: 768px) {
  .footer-content span {
    flex-basis: 50%; /* 在屏幕较窄时，每行显示两个内容 */
  }
}

@media screen and (min-width: 769px) {
  .footer-content span {
    flex-basis: auto; /* 在屏幕较宽时，每行只显示一个内容 */
  }
}
</style>
