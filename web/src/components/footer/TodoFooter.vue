<template>
  <div>
    <!-- 脚部：印记和功能按钮 -->
    <div class="footer">
      Copyright &copy; {{ new Date().getFullYear() }} LiZeC
      <a v-for="c in showConfig" @click="c.f" :key="c.name">{{ c.name }}</a>
    </div>

    <!-- 上传文件的控件 -->
    <input type="file" id="file_selector" style="display: none" @change="uploadFile" />
  </div>
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
}

.footer a {
  text-decoration: none;
  color: #666;
  margin-left: 5px;
  margin-right: 5px;
}
</style>
