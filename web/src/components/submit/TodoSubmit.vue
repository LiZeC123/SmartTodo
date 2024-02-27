<template>
  <div class="header">
    <div class="box">
      <div id="form" @keyup.enter="commitTodo">
        <label for="title" @mousedown.left="$emit('logo')">SmartTodo</label>
        <div v-show="enableSubmit" style="float: right; width: 60%">
          <label for="itemType"></label>
          <select id="itemType" v-model="todoType">
            <option value="single">创建待办</option>
            <option value="file">下载文件</option>
            <option value="note">创建便签</option>
          </select>
          <input
            type="text"
            id="title"
            placeholder="添加ToDo"
            autocomplete="off"
            v-model="todoContent"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, type Ref } from 'vue'
import { parseTitleToData } from './parse'
import type { CreateItem, CreateType, FuncData, TodoType } from './types'

const props = defineProps<{
  enableSubmit?: boolean
}>()


const emit = defineEmits<{
  (e: 'commit', type: CreateType, data: FuncData | CreateItem): void
  (e: 'logo'): void
}>()

let todoContent = ref('')
let todoType: Ref<TodoType> = ref('single')

function commitTodo() {
  const content = todoContent.value.trim()
  if (content === '') {
    alert('TODO不能为空')
    return
  }

  let match = /func (\S+) (.+)/.exec(content)
  if (match !== null) {
    const data: FuncData = { cmd: match[1], data: match[2] }
    emit('commit', 'func', data)
  } else {
    const data = parseTitleToData(todoContent.value, todoType.value)
    if (data.itemType === 'file') {
      emit('commit', 'file', data)
    } else {
      emit('commit', 'create', data)
    }
  }

  // 提交请求后直接清空内容, 而不必等待请求返回, 提高响应速度, 避免重复提交
  todoContent.value = ''
  todoType.value = 'single'
}
</script>

<style scoped>
.header {
  height: 50px;
  background: #333;
  /*background: rgba(47,47,47,0.98);*/
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
  /*首行缩进10px*/
  text-indent: 10px;
  /*圆角边框  好看不止一点点*/
  border-radius: 5px;
  /*盒子阴影 inset内阴影*/
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

/*选中输入框  轮廓的宽度为0*/
input:focus {
  outline-width: 0;
}

label {
  float: left;
  width: 100px;
  line-height: 50px;
  color: #ddd;
  font-size: 24px;
  /*鼠标悬停样式 一只手*/
  cursor: pointer;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}
</style>
@/components/submit/parse
