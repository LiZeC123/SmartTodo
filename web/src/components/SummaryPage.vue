<template>
  <div>
    <h2>统计信息</h2>
    <p>累计完成番茄钟数量: {{ stats.total.count }} 累计学习时间: {{ stats.total.hour }}小时 日均学习时间: {{ stats.total.average }}分钟</p>
    <p>今日完成番茄钟数量: {{ stats.today.count }} 今日累计学习时间: {{ stats.today.minute }}分钟</p>
    <canvas id="myChart"></canvas>

    <item-list title="今日任务(汇总)" :btn-config="[]" :data="todaySummary"
               @checkbox-change="increaseUsedTomatoTime"></item-list>

  </div>
</template>

<script>
import ItemList from "@/components/m/ItemList";

export default {
  name: "SummaryPage",
  components: {ItemList},
  props: {
    updateTodo: Number,
  },
  data: function () {
    return {
      todaySummary: [],
      stats: {
        total: {
          count: 0,
          hour: 0,
          average: 0
        },
        today: {
          count: 0,
          minute: 0,
        },
        week: [0, 0, 0, 0, 0, 0, 0]
      }
    }
  },
  mounted() {
    this.reload()
  },
  computed: {},
  methods: {
    reload: function () {
      this.axios.post("/item/getSummary", {}).then(res => {
        let ans = []
        let data = res.data.items
        for (let key in data) {
          let mList = data[key]
          for (let i = 0; i < mList.length; i++) {
            mList[i].subTask = (i !== 0)
          }
          ans = ans.concat(mList)
        }
        this.todaySummary = ans
        this.stats = res.data.stats

        this.draw()
      })
    },
    draw: function () {
      const labels = [0, 1, 2, 3, 4, 5, 6];

      const data = {
        labels: labels,
        datasets: [{
          label: '近七日专注时长统计',
          backgroundColor: 'rgb(27,141,227)',
          borderColor: 'rgb(27,141,227)',
          data: this.stats.week,
          tension: 0.3,
        }]
      };

      const config = {
        type: 'line',
        data: data,
        options: {
          scales: {
            y: {
              beginAtZero: true
            }
          },
        }
      };

      // eslint-disable-next-line no-undef
      new Chart(
          document.getElementById('myChart'),
          config
      );
    },
    findItem: function (index) {
      return this.todaySummary[index]
    },
    increaseUsedTomatoTime: function (index, id) {
      this.axios.post("/item/increaseUsedTomatoTime", {"id": id}).then(() => {
        let item = this.findItem(index)
        if (item.used_tomato < item.expected_tomato) {
          item.used_tomato += 1
        }
      })
    },
  },
  watch: {
    "updateTodo": function () {
      this.reload()
    },
  }
}
</script>

<style scoped>

</style>