<template>
  <div>
    <tomato-page :reset-count="tomatoResetCount" :reload-count="tomatoReloadCount"
                 @done-task="doneTomatoTask"></tomato-page>
    <item-list title="今日任务" :btnConfig="todayConfig" :data="todayTask"
               @checkbox-change="increaseUsedTomatoTime"></item-list>
    <item-list title="紧急任务" :btnConfig="urgentConfig" :data="urgentTask"
               @checkbox-change="increaseUsedTomatoTime"></item-list>
    <item-list title="活动任务" :btnConfig="activeConfig" :data="activeTask"
               @checkbox-change="toTodayTask"></item-list>
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
      urgentTask: [],
      todayTask: [],
      activeTask: [],
      lastUpdateDate: new Date().getDate(),
      todayConfig: [
        {"name": "long-arrow-alt-down", "desc": "退回此项目", "function": this.backItem},
        {"name": "clock", "desc": "启动番茄钟", "function": this.startTomatoTimer},
        {"name": "sort-amount-up", "desc": "增加预计时间", "function": this.increaseExpectedTomatoTime},
      ],
      urgentConfig: [
        {"name": "long-arrow-alt-down", "desc": "退回此项目", "function": this.backItem},
        {"name": "clock", "desc": "启动番茄钟", "function": this.startTomatoTimer},
        {"name": "sort-amount-up", "desc": "增加预计时间", "function": this.increaseExpectedTomatoTime},
      ],
      activeConfig: [
        {"name": "trash-alt", "desc": "删除此项目", "function": this.removeItem},
        {"name": "biohazard", "desc": "转为紧急任务", "function": this.toUrgentTask},
        {"name": "sort-amount-up", "desc": "增加预计时间", "function": this.increaseExpectedTomatoTime},
      ],
      tomatoResetCount: 0,
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
      if (this.urgentTask.length > index && this.urgentTask[index].id === id) {
        return this.urgentTask
      } else if (this.todayTask.length > index && this.todayTask[index].id === id) {
        return this.todayTask
      } else if (this.activeTask.length > index && this.activeTask[index].id === id) {
        return this.activeTask
      }
      return null
    },
    // findItemById: function (id) {
    //   for (let i = 0; i < this.todayTask.length; i++) {
    //     const e = this.todayTask[i];
    //     if (e.id === id) {
    //       return [i, e]
    //     }
    //   }
    //   for (let i = 0; i < this.urgentTask.length; i++) {
    //     const e = this.urgentTask[i];
    //     if (e.id === id) {
    //       return [i, e]
    //     }
    //   }
    //   return [-1, null]
    // },
    reload: function () {
      this.axios.post("/item/getAll", {"parent": this.parent}).then(res => {
        this.todayTask = res.data.todayTask
        this.urgentTask = res.data.urgentTask
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
        if (item.used_tomato < item.expected_tomato) {
          item.used_tomato += 1
        }
      })
    },
    startTomatoTimer: function (index, id) {
      this.axios.post("/tomato/setTask", {"id": id}).then(() => this.tomatoResetCount += 1)
    },
    toUrgentTask: function (index, id) {
      this.axios.post("/item/toUrgentTask", {"id": id}).then(() => {
        let item = this.activeTask[index]
        this.activeTask.splice(index, 1)
        this.urgentTask.push(item)
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