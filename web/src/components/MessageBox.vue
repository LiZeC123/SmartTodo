<template>
  <div>
    <h2>{{ title }}</h2>
    <!--pre标签能够使文本中的换行符号正确的渲染-->
    <pre class="messageBox" @contextmenu.prevent>{{ message }}</pre>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  message: string
}>()
</script>

<style scoped>
.messageBox {
  resize: vertical;
  overflow: auto;
  border: 1px solid silver;
  border-radius: 5px;
  min-height: 100px;
  box-shadow: inset 0 0 10px silver;
  padding: 1em;
  height: 700px;
  margin-top: 16px;
}
</style>