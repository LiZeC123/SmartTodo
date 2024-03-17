<template>
  <TodoSubmit @logo="gotoHome"></TodoSubmit>
  <div class="container">
    <!-- 番茄钟模块 -->
    <TomatoClock :item="tomatoItem" @done-task="doneTomatoTask"></TomatoClock>
    <TimeLine :items="timeLineItem" :count="countInfo"></TimeLine>
    <ItemList title="今日任务" :btnCfg="tCfg" :data="tTask" @done="doneItem"></ItemList> 
    <Footer :is-admin="false" :config="footerConfig"></Footer>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { type Ref, ref, onMounted } from 'vue'
import router from '@/router'

import TodoSubmit from '@/components/submit/TodoSubmit.vue'
import TomatoClock from '@/components/tomato/TomatoClock.vue'
import ItemList from '@/components/item/ItemList.vue'
import TimeLine from "@/components/timeline/TimeLine.vue"
import Footer from '@/components/footer/TodoFooter.vue'

import { playNotifacationAudio } from '@/components/tomato/tools'
import type { TomatoItem, TomatoEventType, TomatoParam } from '@/components/tomato/types'
import type { Item } from '@/components/item/types'
import type { CountInfo, TimeLineItem, Report } from '@/components/timeline/types'
import type { FooterConfig } from '@/components/footer/types'

onMounted(() => {
  loadTomato()
  loadTomatoItems()
  loadTimeLineItems()
  document.title = '番茄任务'
  window.onfocus = reloadList
})

function reloadList() {
  loadTomatoItems()
  loadTimeLineItems()
}

// ========================================================== TodoSubmit 相关配置 ==========================================================
function gotoHome() {
  document.title = '代办事项列表'
  window.open("/todo")
}


// ========================================================== TomatoClock 相关配置 ==========================================================
let tomatoItem: Ref<TomatoItem | undefined> = ref()

function loadTomato() {
  axios.get<TomatoItem>('/tomato/getTask').then((res) => { tomatoItem.value = res.data })
}

function doneTomatoTask(type: TomatoEventType, param: TomatoParam) {
  if (type === 'undo') {
    const reason = prompt("请输入取消原因")
    if (reason) {
      param.reason = reason
    }

    axios.post('/tomato/undoTask', param).then(() => tomatoItem.value = undefined)
  } else if (type === 'done') {
    axios.post<boolean>('/tomato/finishTask', param).then(res => {
      if (res.data) {
        playNotifacationAudio()
        tomatoItem.value = undefined
        reloadList()
      }
    })
  }
}

// ========================================================== ItemList 相关配置 ==========================================================
let tTask: Ref<Item[]> = ref([])

const tCfg = [
  {
    name: 'clock',
    desc: '启动番茄钟',
    f: (_: number, id: string) => {
      axios.post('/tomato/setTask', { id }).then(() => {
        loadTomato()
      })
    }
  },
]

function loadTomatoItems() {
  axios.post<Item[]>('/item/getTomato').then((res) => { tTask.value = res.data })
}

function doneItem(index: number, id: string) {
  axios.post('/item/incUsedTime', { id }).then(() => (tTask.value[index].used_tomato += 1))
}

// ========================================================== TimeLine 相关配置 ==========================================================
let timeLineItem = ref<TimeLineItem[]>([])
let countInfo = ref<CountInfo>({ tomatoCounts: 0, totalMinutes: 0 })

function loadTimeLineItems() {
  axios.post<Report>("/summary/getReport").then(res => {
    timeLineItem.value = res.data.items
    countInfo.value = res.data.counter
  })
}

// ========================================================== Footer 相关配置 ==========================================================
let footerConfig: FooterConfig[] = [
  { name: '新增记录', needAdmin: false, f: addRecord },
  { name: '总结列表', needAdmin: false, f: () => router.push({ path: '/summary' }) },
]


function addRecord() {
  const name = prompt('请输入记录名称')
  if (!name) {
    return
  }

  const startTime = prompt('请输入开始时间')
  if (!startTime) {
    return
  }

  axios.post('/tomato/addRecord', { name, startTime }).then(reloadList)
}

</script>

<style scoped>
.container {
  max-width: 1000px;
  padding: 0 10px;
  margin: 0 auto;
}
</style>
