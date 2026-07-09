<template>
  <TodoSubmit></TodoSubmit>
  <div class="container">
    <TimeLine :items="timeLineItem" :count="countInfo"></TimeLine>
    <ItemGroupedList title="" :data="tTask" :disable="true"></ItemGroupedList>
    <ItemGroupedList title="临期任务汇总" :data="dlTask" :disable="true"></ItemGroupedList>
    <Footer :is-admin="false" :config="footerConfig"></Footer>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref, type Ref } from 'vue'

import TodoSubmit from '@/components/submit/TodoSubmit.vue'
import TimeLine from "@/components/timeline/TimeLine.vue"
import ItemGroupedList from '@/components/item/ItemGroupedList.vue'
import Footer from '@/components/footer/TodoFooter.vue'

import type { CountInfo, TimeLineItem, Report } from '@/components/timeline/types'
import type { FooterConfig } from '@/components/footer/types'
import type { GroupedItem } from '@/components/item/types'


onMounted(() => {
  loadTimeLineItems()
  loadItemWithSubTask()
  loadDLItem()
  document.title = '总结列表'
})



// ========================================================== TimeLine 相关配置 ==========================================================
let timeLineItem = ref<TimeLineItem[]>([])
let countInfo = ref<CountInfo>({ tomatoCounts: 0, totalMinutes: 0 })

function loadTimeLineItems() {
  axios.post<Report>("/summary/getReport").then(res => {
    timeLineItem.value = res.data.items
    countInfo.value = res.data.counter
  })
}


// ========================================================== ItemGroupedList 相关配置 ==========================================================

let tTask: Ref<GroupedItem[]> = ref([])

function loadItemWithSubTask() {
  axios.post<GroupedItem[]>('/item/getItemWithSubTask').then((res) => { tTask.value = res.data })
}

// ========================================================== ItemList 相关配置 ==========================================================
let dlTask: Ref<GroupedItem[]> = ref([])

function loadDLItem() {
  axios.post<GroupedItem[]>('/item/getDeadlineItem').then((res) => { dlTask.value = res.data })
}





// ========================================================== Footer 相关配置 ==========================================================
let footerConfig: FooterConfig[] = []

</script>

<style scoped>
.container {
  max-width: 1000px;
  padding: 0 10px;
  margin: 0 auto;
}
</style>