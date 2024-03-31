<template>
  <TodoSubmit @logo="gotoHome"></TodoSubmit>
  <div class="container">
    <TimeLine :items="timeLineItem" :count="countInfo"></TimeLine>
    <EventTime :items="eventLineItem"></EventTime>
    <SmartAnalysis :report="smartReport"></SmartAnalysis>
    <ItemGroupedList title="" :data="tTask"></ItemGroupedList> 
    <ItemList title="临期任务汇总" :data="dlTask" ></ItemList>
    <h2>今日总结</h2>
    <NoteEditor :init-content="initContent" @save="saveNote"></NoteEditor>
    <Footer :is-admin="false" :config="footerConfig"></Footer>
    <AlertBox :text="alertText"></AlertBox>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref, type Ref } from 'vue'
import router from '@/router'

import TodoSubmit from '@/components/submit/TodoSubmit.vue'
import TimeLine from "@/components/timeline/TimeLine.vue"
import EventTime from '@/components/eventline/EventLine.vue'
import SmartAnalysis from '@/components/analysis/SmartAnalysis.vue'
import ItemGroupedList from '@/components/item/ItemGroupedList.vue'
import ItemList from '@/components/item/ItemList.vue'
import NoteEditor from '@/components/editor/NoteEditor.vue'
import Footer from '@/components/footer/TodoFooter.vue'
import AlertBox from '@/components/AlertBox.vue'

import type { CountInfo, TimeLineItem, Report } from '@/components/timeline/types'
import type { EventItem } from '@/components/eventline/types'
import type {SmartAnalysisReport} from '@/components/analysis/types'
import type { FooterConfig } from '@/components/footer/types'
import type { GroupedItem, Item } from '@/components/item/types'


onMounted(() => {
  loadTimeLineItems()
  loadEventLineItems()
  loadAnalysisReport()
  loadItemWithSubTask()
  loadDLItem()
  loadNote()
  document.title = '总结列表'
})

// ========================================================== TodoSubmit 相关配置 ==========================================================
function gotoHome() {
  document.title = '代办事项列表'
  router.push({ path: '/todo' })
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

// ========================================================== EventLine 相关配置 ==========================================================
let eventLineItem = ref<EventItem[]>([])

function loadEventLineItems() {
  axios.post<EventItem[]>("/summary/getEventLine").then(res => {
    eventLineItem.value = res.data
  })
}

// ========================================================== SmartAnalysis 相关配置 ==========================================================

let smartReport = ref<SmartAnalysisReport>({count: 0, groups: []})


function loadAnalysisReport() {
  axios.post<SmartAnalysisReport>("/summary/getSmartReport").then(res => {
    smartReport.value = res.data
  })
}

// ========================================================== ItemGroupedList 相关配置 ==========================================================

let tTask: Ref<GroupedItem[]> = ref([])

function loadItemWithSubTask() {
  axios.post<GroupedItem[]>('/item/getItemWithSubTask').then((res) => { tTask.value = res.data })
}

// ========================================================== ItemList 相关配置 ==========================================================
let dlTask: Ref<Item[]> = ref([])

function loadDLItem() {
  axios.post<Item[]>('/item/getDeadlineItem').then((res) => { dlTask.value = res.data })
}


// ========================================================== NoteEditor 相关配置 ==========================================================
let initContent = ref("")

function loadNote() {
  axios.post<string>("/summary/getNote").then(res => initContent.value = res.data)
}

function saveNote(content: string) {
  axios.post("/summary/updateNode", { content }).then(() => {
    alertText.value = '文档已保存'
    setTimeout(() => (alertText.value = undefined), 500)
  })
}


// ========================================================== Footer 相关配置 ==========================================================
let footerConfig: FooterConfig[] = []


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