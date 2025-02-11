<template>
    <TodoSubmit></TodoSubmit>

    <Footer :is-admin="false" :config="footerConfig"></Footer>
</template>


<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref, type Ref } from 'vue'
import router from '@/router'

import TodoSubmit from '@/components/submit/TodoSubmit.vue'
import Footer from '@/components/footer/TodoFooter.vue'

import type { FooterConfig } from '@/components/footer/types'




// ========================================================== Footer 相关配置 ==========================================================
let footerConfig: FooterConfig[] = []

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

</style>