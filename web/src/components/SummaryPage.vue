<template>
  <div>
    <item-list title="今日任务(汇总)" :btn-config="[]" :data="todaySummary"
               @checkbox-change="increaseUsedTomatoTime"></item-list>
  </div>
</template>

<script>
import ItemList from "@/components/m/ItemList";

export default {
  name: "SummaryPage",
  components: {ItemList},
  data: function () {
    return {
      todaySummary: [],
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
        let data = res.data
        for (let key in data) {
          let mList = data[key]
          for (let i = 0; i < mList.length; i++) {
            mList[i].subTask = (i !== 0)
          }
          ans = ans.concat(mList)
        }
        this.todaySummary = ans
      })
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
  watch: {}
}
</script>

<style scoped>

</style>