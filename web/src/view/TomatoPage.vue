<template>
  <TodoSubmit @logo="gotoHome"></TodoSubmit>
  <div class="container">
    <!-- 番茄钟模块 -->
    <TomatoClock :item="tomatoItem" @done-task="doneTomatoTask"></TomatoClock>
    <TimeLine :items="timeLineItem" :count="countInfo"></TimeLine>
    <ItemGroupedList title="今日任务" :btnCfg="tCfg" :data="tTask" @done="doneItem"></ItemGroupedList>
    <Footer :is-admin="false" :config="footerConfig"></Footer>
    <AlertBox :text="alertText"></AlertBox>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { type Ref, ref, onMounted } from 'vue'
import router from '@/router'

import TodoSubmit from '@/components/submit/TodoSubmit.vue'
import TomatoClock from '@/components/tomato/TomatoClock.vue'
import ItemGroupedList from '@/components/item/ItemGroupedList.vue'
import TimeLine from "@/components/timeline/TimeLine.vue"
import Footer from '@/components/footer/TodoFooter.vue'

import { playNotifacationAudio, playNotifacationAudioShort } from '@/components/tomato/tools'
import type { TomatoItem, TomatoEventType, TomatoParam } from '@/components/tomato/types'
import type { GroupedItem } from '@/components/item/types'
import type { CountInfo, TimeLineItem, Report } from '@/components/timeline/types'
import type { FooterConfig } from '@/components/footer/types'
import AlertBox from '@/components/AlertBox.vue'

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
      axios.post('/tomato/undoTask', param).then(() => tomatoItem.value = undefined)
    }
  } else if (type === 'done' || type === 'auto') {
    axios.post<boolean>('/tomato/finishTask', param).then(res => {
      if (res.data) {
        type === 'auto' ? playNotifacationAudio() : playNotifacationAudioShort()
        tomatoItem.value = undefined
        reloadList()
      }
    })
  }
}

// ========================================================== ItemGroupedList 相关配置 ==========================================================
let tTask: Ref<GroupedItem[]> = ref([])

const tCfg = [
  {
    name: 'angle-double-down',
    desc: '退回此项目',
    f: (_: number, id: string) => {
      axios.post('/item/back', { id }).then(() => {
        loadTomatoItems()
      })
    }
  },
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
  axios.post<GroupedItem[]>('/item/getTomato').then((res) => { tTask.value = res.data })
}

function doneItem(index: number, id: string) {
  axios.post('/item/incUsedTime', { id }).then(loadTomatoItems)
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
