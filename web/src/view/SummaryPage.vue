<template>
  <div class="container">
    <h2>任务时间轴</h2>
    <TimeLine :items="timeLineItem" :count="countInfo"></TimeLine>
    <h2>事件时间轴</h2>
    <EventTime :items="eventLineItem"></EventTime>
    <h2>智能分析</h2>

    <!-- TODO:  myChart -->

    <h2>今日总结</h2>
    <NoteEditor :init-content="initContent" @save="saveNote"></NoteEditor>

    <AlertBox :text="alertText" :show="alertShow"></AlertBox>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref } from 'vue';

import TimeLine from "@/components/timeline/TimeLine.vue"
import EventTime from '@/components/eventline/EventLine.vue'
import NoteEditor from '@/components/editor/NoteEditor.vue'
import AlertBox from '@/components/AlertBox.vue'

import type { CountInfo, TimeLineItem, Report } from '@/components/timeline/types'
import type { EventItem } from '@/components/eventline/types'


onMounted(() => {
  loadTimeLineItems()
  loadEventLineItems()
  loadNote()
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

// ========================================================== EventLine 相关配置 ==========================================================
let eventLineItem = ref<EventItem[]>([])

function loadEventLineItems() {
  axios.post<EventItem[]>("/summary/getEventLine").then(res => {
    eventLineItem.value = res.data
  })
}



// ========================================================== NoteEditor 相关配置 ==========================================================
let initContent = ref("每日总结")

function loadNote() {
  axios.post<string>("/summary/getNote").then(res => initContent.value = res.data)
}

function saveNote(content: string) {
  axios.post("/summary/updateNode", { content }).then(() => {
    alertText.value = '文档已保存'
    alertShow.value = true
    setTimeout(() => (alertShow.value = false), 500)
  })
}


// ========================================================== Alert 相关配置 ==========================================================
let alertText = ref('')
let alertShow = ref(false)



// import ItemList from "@/components/m/ItemList";
// import MessageBox from "@/components/m/MessageBox";

// export default {
//   name: "SummaryPage",
//   components: {MessageBox, ItemList},
//   props: {
//     updateTodo: Number,
//   },
//   data: function () {
//     return {
//       todaySummary: [],
//       stats: {
//         total: {
//           count: 0,
//           hour: 0,
//           average: 0
//         },
//         today: {
//           count: 0,
//           minute: 0,
//         },
//         week: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
//       },
//       habitSummary: [],
//       dailyReport: "",
//     }
//   },
//   mounted() {
//     this.reload()
//   },
//   computed: {},
//   methods: {
//     reload: function () {
//       document.title = "任务统计"

//       this.axios.post("/item/getSummary", {}).then(res => {
//         let ans = []
//         let data = res.data.items
//         for (let key in data) {
//           let mList = data[key]
//           for (let i = 0; i < mList.length; i++) {
//             mList[i].subTask = (i !== 0)
//           }
//           ans = ans.concat(mList)
//         }
//         this.todaySummary = ans
//         this.stats = res.data.stats
//         this.habitSummary = res.data.habit

//         this.draw()
//       })

//       this.axios.get("/item/dailyReport").then(res => {
//         console.log(res)
//         this.dailyReport = res.data
//       })
//     },
//     draw: function () {
//       const labels = getDateArray();

//       const data = {
//         labels: labels,
//         datasets: [{
//           label: '近期日专注时长统计',
//           backgroundColor: 'rgb(27,141,227)',
//           borderColor: 'rgb(27,141,227)',
//           data: this.stats.week,
//           tension: 0.3,
//         }]
//       };

//       const config = {
//         type: 'line',
//         data: data,
//         options: {
//           scales: {
//             y: {
//               beginAtZero: true
//             }
//           },
//         }
//       };

//       // eslint-disable-next-line no-undef
//       new Chart(
//           document.getElementById('myChart'),
//           config
//       );
//     },
//     findItem: function (index) {
//       return this.todaySummary[index]
//     },
//     increaseUsedTomatoTime: function (index, id) {
//       this.axios.post("/item/increaseUsedTomatoTime", {"id": id}).then(() => {
//         let item = this.findItem(index)
//         if (item.used_tomato < item.expected_tomato) {
//           item.used_tomato += 1
//         }
//       })
//     },
//   },
//   watch: {
//     "updateTodo": function () {
//       this.reload()
//     },
//   }
// }

// function getDateArray() {
//   let array = []
//   for (let i = 0; i < 15; i++) {
//     array.push(getDay(-i));
//   }

//   return array
// }

// function getDay(change) {
//   let today = new Date()
//   const target = today.getTime() + 1000 * 60 * 60 * 24 * change;

//   today.setTime(target)

//   return (today.getMonth() + 1) + "." + (today.getDate())
// }


</script>

<style scoped>
.container {
  max-width: 1000px;
  padding: 0 10px;
  margin: 0 auto;
}
</style>