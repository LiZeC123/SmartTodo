<template>
  <div class="header">
    <div class="box">
      <div id="form">
        <label for="title" @mousedown.left="gotoHome">
          <span class="full-text">SmartTodo</span>
          <span class="short-text">Todo</span>
        </label>
        <div v-show="enableSubmit">
          <label for="itemType"></label>
          <select id="itemType" v-model="priority">
            <option value="" disabled selected>请选择优先级</option>
            <option value="p0">高优任务</option>
            <option value="p1">普通任务</option>
            <option value="p2">低优任务</option>
          </select>
          <input type="text" id="title" placeholder="添加ToDo" autocomplete="off" v-model="todoContent"
            enterkeyhint="done" @keydown.enter.prevent="commitTodo" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, type Ref } from 'vue'
import { parseTitleToData } from './parse'
import type { CreateItem, CreateType, FuncData, TodoPriority } from './types'
import router from '@/router'

const props = defineProps<{
  enableSubmit?: boolean
  homePath?: string
}>()

const emit = defineEmits<{
  (e: 'commit', type: CreateType, data: FuncData | CreateItem): void
}>()

function gotoHome() {
  document.title = '待办事项列表'
  if (props.homePath !== undefined) {
    router.push({ path: props.homePath })
  } else {
    router.push({ path: '/' })
  }
}

const todoContent = ref('')
const priority: Ref<TodoPriority> = ref('')  // 无默认值，必须手动选择

function commitTodo() {
  const content = todoContent.value.trim()
  if (content === '') {
    alert('TODO不能为空')
    return
  }


  let match = /func (\S+) (.+)/.exec(content)
  if (match !== null) {
    // 执行指令无需选择优先级
    const data: FuncData = { cmd: match[1], data: match[2] }
    emit('commit', 'func', data)
  } else {
    // 创建待办事项时, 如果显示优先级选择器，则必须选择有效优先级
    if (props.enableSubmit && !priority.value) {
      alert('请先选择优先级')
      return
    }

    const data = parseTitleToData(todoContent.value, priority.value)
    if (data.itemType === 'file') {
      emit('commit', 'file', data)
    } else {
      emit('commit', 'create', data)
    }
  }

  todoContent.value = ''
  priority.value = ''   // 重置优先级，下次必须重新选择
}
</script>

<style scoped>
.header {
  height: 50px;
  background: #333;
}

.header .box {
  max-width: 1000px;
  padding: 0 10px;
  margin: 0 auto;
}

.header input {
  float: right;
  width: 73%;
  height: 24px;
  margin-top: 12px;
  text-indent: 10px;
  border-radius: 5px;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.24),
    0 1px 6px rgba(0, 0, 0, 0.45) inset;
  border: none;
}

.header select {
  margin-top: 12px;
  height: 26px;
  width: 25%;
  border-radius: 5px;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.24),
    0 1px 6px rgba(0, 0, 0, 0.45) inset;
  border: none;
}

input:focus {
  outline-width: 0;
}

/* 默认显示完整名称，隐藏短名称 */
.header label .short-text {
  display: none;
}

.header label {
  float: left;
  width: 100px;
  line-height: 50px;
  color: #ddd;
  font-size: 24px;
  cursor: pointer;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

  .header #form>div {
    float:right;
    width: 60%;
  }

/* ========= 手机窄屏适配 ========= */
@media (max-width: 600px) {

  /* 显示短名称 Todo，隐藏完整名称 SmartTodo */
  .header label .full-text {
    display: none;
  }

  .header label .short-text {
    display: inline;
  }

  /* 释放 label 占用的宽度 */
  .header label {
    width: auto;
    font-size: 20px;
    margin-right: 6px;
  }

  /* 调整下拉框和输入框宽度，给右侧留更多空间 */
  .header select {
    width: 30%;
  }

  .header input {
    width: 65%;
  }

  /* 保证右侧容器布局不乱 (原有 float:right 宽度 60% 保持不变) */
  .header #form>div {
    float:right;
    width: 80%;
  }
}
</style>