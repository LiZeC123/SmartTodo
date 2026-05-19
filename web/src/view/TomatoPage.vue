<template>
  <TodoSubmit></TodoSubmit>
  <div class="container">
    <!-- 番茄钟模块 -->
    <TomatoClock :item="tomatoItem" @done-task="doneTomatoTask" @rest-finished="tomatoFinished"></TomatoClock>
    <ItemGroupedList title="今日任务" :btnCfg="tCfg" :data="tTask" @done="doneItem"></ItemGroupedList>
    <TimeLine :items="timeLineItem" :count="countInfo"></TimeLine>
    <Footer :is-admin="false" :config="footerConfig"></Footer>
    <AlertBox :text="alertText"></AlertBox>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref, type Ref } from 'vue'

import TodoSubmit from '@/components/submit/TodoSubmit.vue'
import TomatoClock from '@/components/tomato/TomatoClock.vue'
import ItemGroupedList from '@/components/item/ItemGroupedList.vue'
import TimeLine from '@/components/timeline/TimeLine.vue'
import Footer from '@/components/footer/TodoFooter.vue'

import type { TomatoEventType, TomatoItem, TomatoParam } from '@/components/tomato/types'
import type { GroupedItem } from '@/components/item/types'
import type { CountInfo, Report, TimeLineItem } from '@/components/timeline/types'
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

// ========================================================== TomatoClock 相关配置 ==========================================================
let tomatoItem: Ref<TomatoItem | undefined> = ref()

function loadTomato() {
  axios.get<TomatoItem>('/tomato/getTask').then((res) => {
    tomatoItem.value = res.data
  })
}

function doneTomatoTask(type: TomatoEventType, param: TomatoParam) {
  
  if (type === 'undo') {
    const reason = prompt('请输入取消原因')
    if (reason) {
      param.reason = reason
      axios.post('/tomato/undoTask', param).then(() => (tomatoItem.value = undefined))
    }
    return
  }
    
  if (type === 'done') {
    // 手动需求还是需要请求后台并刷新状态
    axios.post<boolean>('/tomato/finishTask', param).then((res) => {
      if (res.data) {
        tomatoItem.value = undefined
        reloadList()
      }
    })
  }
}

function tomatoFinished() {
  // 当前番茄钟完成了工作和休息的倒计时, 更新一下后台状态
  // 这里可以略微延迟一段时间后再查询
  setTimeout(() => {
    loadTomato()
    setTimeout(reloadList, 200)
  }, 200)
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
        // 由于列表可能很长, 因此如果启动番茄钟成功, 则滚动到顶部, 以便于用户感知到当前启动的番茄钟
        window.scrollTo({
          top: 0,
          behavior: "smooth" // 平滑滚动，去掉就是瞬间跳回顶部
        })
      })
    }
  }
]

function loadTomatoItems() {
  axios.post<GroupedItem[]>('/item/getTomato').then((res) => {
    tTask.value = res.data
  })
}

function doneItem(index: number, id: string) {
  axios.post('/item/incUsedTime', { id }).then(loadTomatoItems)
}

// ========================================================== TimeLine 相关配置 ==========================================================
let timeLineItem = ref<TimeLineItem[]>([])
let countInfo = ref<CountInfo>({ tomatoCounts: 0, totalMinutes: 0 })

function loadTimeLineItems() {
  axios.post<Report>('/summary/getReport').then((res) => {
    timeLineItem.value = res.data.items
    countInfo.value = res.data.counter
  })
}

// ========================================================== Footer 相关配置 ==========================================================
let footerConfig: FooterConfig[] = [
  { name: '新增记录', needAdmin: false, f: addRecord },
  { name: '总结列表', needAdmin: false, f: () => window.open('/summary') }
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
