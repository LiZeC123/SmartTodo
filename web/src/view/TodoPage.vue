<template>
  <TodoSubmit :enableSubmit="true" @commit="doCommitTodo"></TodoSubmit>

  <div class="container">
    <!-- 代办事项模块 -->
    <ItemList title="今日任务" :btnCfg="tCfg" :data="tTask" @done="(idx, id) => incTime(tTask)(idx, id)"
      @item-click="itemClick" @header-click="openTomatoPage">
    </ItemList>
    <ItemList title="活动清单" :btnCfg="aCfg" :data="aTask" @done="(idx, id) => incTime(aTask)(idx, id)"
      @item-click="itemClick">
    </ItemList>

    <!-- Note编辑器, 仅对Note类型页面生效  -->
    <NoteEditor v-if="initContent" :init-content="initContent" @save="saveNote"></NoteEditor>

    <TodoFooter :is-admin="isAdmin" :config="footerConfig" @upload-file="uploadFile"></TodoFooter>

    <AlertBox :text="alertText"></AlertBox>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref, type Ref } from 'vue'
import { useRoute } from 'vue-router'
import router from '@/router'

import TodoSubmit from '@/components/submit/TodoSubmit.vue'
import ItemList from '@/components/item/ItemList.vue'
import NoteEditor from '@/components/editor/NoteEditor.vue'
import TodoFooter from '@/components/footer/TodoFooter.vue'
import AlertBox from '@/components/AlertBox.vue'

import type { CreateType, CreateItem, FuncData } from '@/components/submit/types'
import type { Item } from '@/components/item/types'
import type { FooterConfig } from '@/components/footer/types'
import { selectFile } from '@/components/footer/tools'
import { byCalcValue, byUpdateTime } from '@/components/item/sort'

const $router = useRoute()
// 父Item的Id, 对于主界面, 此属性为undefined, 对于Note页面, 此属性为父Item的ID
let parent: string | undefined = undefined

onMounted(() => {
  parent = $router.params.id as string
  loadItem()
  loadNote()
  loadIsAdmin()
  window.onfocus = loadItem
})

// ========================================================== TodoSubmit 相关配置 ==========================================================
function doCommitTodo(type: CreateType, data: FuncData | CreateItem) {
  // 1. 注入parent属性
  data.parent = parent
  if (type === 'func') {
    axios.post('/admin/func', data).then(loadItem)
  } else if (type === 'file') {
    // 由于文件下载可能耗时较长, 因此需要先创建一个占位符来提示用户已经提交成功
    createFilePlaceHold('文件正在下载,请稍等...')
    axios.post('/item/create', data).then(loadItem)
  } else if (type === 'create') {
    axios.post('/item/create', data).then(loadItem)
  } else {
    throw new Error('未知的Create类型')
  }
}


// ========================================================== ItemList 相关配置 ==========================================================
let tTask: Ref<Item[]> = ref([])
let aTask: Ref<Item[]> = ref([])

const tCfg = [
  {
    name: 'angle-double-down',
    desc: '退回此项目',
    f: (index: number, id: string) => {
      axios.post<boolean>('/item/back', { id }).then(() => {
        aTask.value.push(...tTask.value.splice(index, 1))
        aTask.value.sort(byCalcValue)
      })
    }
  },
  {
    name: 'calculator',
    desc: '增加预计时间',
    f: (index: number, id: string) => {
      const expT = tTask.value[index].expected_tomato
      if (expT >= 4) {
        alert("单个任务的番茄钟数量不建议超过4个")
      } else {
        axios.post('/item/incExpTime', { id }).then(() => (tTask.value[index].expected_tomato += 1))
      }
    }
  }
]

const aCfg = [
  {
    name: 'trash-alt',
    desc: '删除此项目',
    f: (index: number, id: string) => {
      axios.post('/item/remove', { id }).then(() => aTask.value.splice(index, 1))
    }
  },
  {
    name: 'list-ol',
    desc: '转为今日任务',
    f: (index: number, id: string) => {
      axios.post('/item/toTodayTask', { id }).then(() => {
        // aTask.value[index].create_time = new Date().toISOString()
        tTask.value.push(...aTask.value.splice(index, 1))
      })
    }
  }
]

interface AllData {
  todayTask: Item[]
  activeTask: Item[]
}

function loadItem() {
  axios.post<AllData>('/item/getAll', { parent }).then((res) => {
    tTask.value = res.data.todayTask
    // 今日任务按照添加顺序排序
    tTask.value.sort(byUpdateTime)
    aTask.value = res.data.activeTask
    // 活动清单需要按照重要程度进行排序
    aTask.value.sort(byCalcValue)
  })
}


function incTime(xTask: Item[]) {
  return (index: number, id: string) => {
    axios.post('/item/incUsedTime', { id }).then(() => (xTask[index].used_tomato += 1))
  }
}


function createFilePlaceHold(name: string) {
  const item: Item = {
    id: '1',
    name,
    item_type: 'file',
    create_time: new Date().toISOString(),
    update_time: new Date().toISOString(),
    repeatable: false,
    specific: 0,
    expected_tomato: 1,
    used_tomato: 0
  }
  tTask.value.unshift(item)
}

function itemClick(event: MouseEvent, item: Item) {
  if (event.button === 2) {
    alertText.value = '链接已复制'
    setTimeout(() => (alertText.value = undefined), 500)
  }
}

function openTomatoPage() {
  window.open('/tomato')
}


// ========================================================== NoteEditor 相关配置 ==========================================================
let initContent = ref('')

function loadNote() {
  if (parent === undefined) {
    return
  }

  const data = { id: parent }
  axios.post<string>('/item/getTitle', data).then((res) => (document.title = res.data))
  axios.post<string>('/note/content', data).then((res) => (initContent.value = res.data))
}

function saveNote(content: string) {
  axios.post('note/update', { id: parent, content }).then(() => {
    alertText.value = '文档已保存'
    setTimeout(() => (alertText.value = undefined), 500)
  })
}


// ========================================================== Footer 相关配置 ==========================================================
let footerConfig: FooterConfig[] = [
  { name: '总结列表', needAdmin: false, f: () => router.push({ path: '/summary' }) },
  { name: '上传文件', needAdmin: false, f: selectFile },
  { name: '查看日志', needAdmin: true, f: () => router.push({ path: '/log/log' }) },
  {
    name: '退出登录',
    needAdmin: false,
    f: () => {
      axios.post("/logout")
      router.push({ path: '/login' })
    }
  }
]

let isAdmin = ref(false)

function loadIsAdmin() {
  axios.get<boolean>('/meta/isAdmin').then((rep) => (isAdmin.value = rep.data))
}

function uploadFile(file: File | undefined) {
  if (file === undefined) {
    alert('请选择上传文件')
    return
  }

  createFilePlaceHold('文件正在上传, 请稍等...')

  const form = new FormData()
  form.append('myFile', file)
  if (parent) {
    form.append('parent', parent)
  }

  const config = { headers: { 'Content-Type': 'multipart/form-data' } }

  axios.post('/file/upload', form, config).then(loadItem)
}


// ========================================================== Alert 相关配置 ==========================================================
let alertText: Ref<string | undefined> = ref('')

</script>

<style scoped>
.container {
  max-width: 1000px;
  padding: 0 10px;
  margin: 0 auto;
}
</style>
