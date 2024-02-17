<template>
  <div>
    <span>{{ showSaveState }}</span> <span @click="save" style="float: right">保存文档</span>
  </div>
  <div
    id="editor"
    contenteditable="true"
    @keydown.tab="tab"
    @keydown="hotKeyDispatcher"
    @input="contentUpdated = true"
    v-html="initContent"
  ></div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { doAction, line, note, tab } from './editor'

defineProps<{ initContent: string }>()

const emit = defineEmits<{
  (e: 'save', content: string): void
}>()

let contentUpdated = ref(false)

const showSaveState = computed(() => (contentUpdated.value ? '文档已发生更改' : '文档已保存'))

onMounted(() => {
  // 关闭页面时如果未保存则执行保存操作
  window.onbeforeunload = checkUnsaved
  // 设置自动保存
  setInterval(autoSave, 30 * 1000)
})

function checkUnsaved(e: BeforeUnloadEvent) {
  if (contentUpdated.value) {
    e.preventDefault()
    e.returnValue = false // 设置为false来弹窗阻止关闭
  }
}

function save() {
  let content = document.getElementById('editor')?.innerHTML
  if (content === undefined) {
    return
  }
  emit('save', content)
  contentUpdated.value = false
}

function autoSave() {
  if (contentUpdated.value) {
    save()
  }
}

function hotKeyDispatcher(e: KeyboardEvent) {
  const isCtrl = e.ctrlKey || e.metaKey
  if (isCtrl && e.key === 's') {
    e.preventDefault()
    save()
  } else if (isCtrl && e.key === 'b') {
    e.preventDefault()
    doAction('bold')
  } else if (isCtrl && e.key === 'i') {
    e.preventDefault()
    doAction('italic')
  } else if (isCtrl && e.key === 'u') {
    e.preventDefault()
    doAction('underline')
  } else if (isCtrl && e.key === 'd') {
    e.preventDefault()
    doAction('strikeThrough')
  } else if (isCtrl && e.key === '1') {
    e.preventDefault()
    doAction('h1')
  } else if (isCtrl && e.key === '2') {
    e.preventDefault()
    doAction('h2')
  } else if (isCtrl && e.key === 'h') {
    e.preventDefault()
    line(e)
  } else if (isCtrl && e.key === 'o') {
    e.preventDefault()
    note(e)
  }
}
</script>

<style>
#editor {
  resize: vertical;
  overflow: auto;
  border: 1px solid silver;
  border-radius: 5px;
  min-height: 100px;
  box-shadow: inset 0 0 10px silver;
  padding: 1em;
}

blockquote {
  position: relative;
  padding: 1px 5px;
  border-left: 4px solid #3d89db;
  /*color: #6e6e6e;*/
  background: #d2d2d2;
  /*font-size: 14px;*/
  border-radius: 0 2px 2px 0;
  margin: 0 0;
}
</style>
