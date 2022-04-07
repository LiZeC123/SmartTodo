<template>
  <div>
    <tomato-page :reload-count="tomatoReloadCount" @done-task="doneTomatoTask"></tomato-page>
    <item-list title="今日任务" :btnConfig="todayConfig" :data="todayTask"
               @checkbox-change="increaseUsedTomatoTime"></item-list>
    <item-list title="活动清单" :btnConfig="activeConfig" :data="activeTask"
               @checkbox-change="increaseUsedTomatoTime"></item-list>
  </div>
</template>

<script>
import ItemList from "@/components/m/ItemList";
import TomatoPage from "@/components/m/TomatoItem";

export default {
  name: "TodoPage",
  components: {TomatoPage, ItemList},
  props: {
    updateTodo: Number,
    createPlaceHold: Number,
    parent: String,
  },
  data: function () {
    return {
      todayTask: [],
      activeTask: [],
      lastUpdateDate: new Date().getDate(),
      todayConfig: [
        {"name": "angle-double-down", "desc": "退回此项目", "function": this.backItem},
        {"name": "clock", "desc": "启动番茄钟", "function": this.startTomatoTimer},
        {"name": "calculator", "desc": "增加预计时间", "function": this.increaseExpectedTomatoTime},
      ],
      activeConfig: [
        {"name": "trash-alt", "desc": "删除此项目", "function": this.removeItem},
        {"name": "list-ol", "desc": "转为今日任务", "function": this.toTodayTask},
        {"name": "calculator", "desc": "增加预计时间", "function": this.increaseExpectedTomatoTime},
      ],
      tomatoReloadCount: 0,
    }
  },
  created() {
    this.reload();
  },
  mounted() {
    window.onfocus = this.checkUpdateStatus
  },
  methods: {
    findItem: function (index, id) {
      if (this.todayTask.length > index && this.todayTask[index].id === id) {
        return this.todayTask
      } else if (this.activeTask.length > index && this.activeTask[index].id === id) {
        return this.activeTask
      }
      return null
    },
    reload: function () {
      this.axios.post("/item/getAll", {"parent": this.parent}).then(res => {
        this.todayTask = res.data.todayTask
        this.activeTask = res.data.activeTask
      })
    },
    backItem: function (index, id) {
      this.axios.post("/item/back", {"id": id, "parent": this.parent}).then(res => {
        this.findItem(index, id).splice(index, 1)
        this.activeTask = res.data
      })
    },
    removeItem: function (index, id) {
      this.axios.post("/item/remove", {"id": id}).then(() => this.findItem(index, id).splice(index, 1))
    },
    increaseExpectedTomatoTime: function (index, id) {
      this.axios.post("/item/increaseExpectedTomatoTime", {"id": id}).then(() => this.findItem(index, id)[index].expected_tomato += 1)
    },
    increaseUsedTomatoTime: function (index, id) {
      this.axios.post("/item/increaseUsedTomatoTime", {"id": id}).then(() => {
        let item = this.findItem(index, id)[index]
        if (item.habit_expected !== 0 && (item.habit_done < item.habit_expected) || item.habit_expected === -1) {
          item.habit_done += 1
          item.used_tomato = 1 // 前端变成完成样式
        } else if (item.used_tomato < item.expected_tomato) {
          item.used_tomato += 1
        }
      })
    },
    startTomatoTimer: function (index, id) {
      this.axios.post("/tomato/setTask", {"id": id}).then(() => {
        this.tomatoReloadCount += 1
        this.reload()
      })
    },
    toTodayTask: function (index, id) {
      this.axios.post("/item/toTodayTask", {"id": id}).then(() => {
        let item = this.activeTask[index]
        this.activeTask.splice(index, 1)
        this.todayTask.push(item)
      })
    },
    checkUpdateStatus: function () {
      const today = new Date().getDate();
      if (today !== this.lastUpdateDate) {
        console.log("检测到日期变化, 刷新当前页面")
        this.reload()
        this.lastUpdateDate = today
      }

      // 只要重新回到当前页面, 就刷新番茄钟状态
      this.tomatoReloadCount += 1
    },
    doneTomatoTask: function (type) {
      if (type === 'done') {
        this.reload()
      }
    }
  },
  watch: {
    "updateTodo": function () {
      this.reload()
      this.tomatoReloadCount += 1
    },
    "createPlaceHold": function () {
      this.activeTask.unshift({
        "id": 1,
        "name": "文件正在下载,请稍等...",
        "item_type": "file",
        "urgent": 0,
        "deadline": null,
        "old": false,
        "repeatable": false,
        "specific": 0,
        "work": false,
        "url": "#",
        "expected_tomato": 1,
        "used_tomato": 0,
      })
    }
  }
}


</script>

<style scoped>

</style>