<template>
  <div>
    <item-list title="今日任务" :btnConfig="todayConfig" :data="todayTask"
               @checkbox-change="finishTask"></item-list>
    <item-list title="紧急任务" :btnConfig="urgentConfig" :data="urgentTask"
               @checkbox-change="finishTask"></item-list>
    <item-list title="活动任务" :btnConfig="activeConfig" :data="activeTask"></item-list>
  </div>
</template>

<script>
import ItemList from "@/components/list/ItemList";

export default {
  name: "TodoComponent",
  components: {ItemList},
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
      lastUpdateDate: new Date().getDate() - 1,
      todayConfig: [
        {"name": "↓", "desc": "退回此项目", "function": this.backItem},
        {"name": "T", "desc": "启动番茄钟", "function": this.startTomatoTimer},
        {"name": "U", "desc": "增加已用时间", "function": this.increaseUsedTomatoTime},
        {"name": "E", "desc": "增加预计时间", "function": this.increaseExpectedTomatoTime},
      ],
      urgentConfig: [
        {"name": "↓", "desc": "退回此项目", "function": this.backItem},
        {"name": "T", "desc": "启动番茄钟", "function": this.startTomatoTimer},
        {"name": "U", "desc": "增加已用时间", "function": this.increaseUsedTomatoTime},
        {"name": "E", "desc": "增加预计时间", "function": this.increaseExpectedTomatoTime},
      ],
      activeConfig: [
        {"name": "-", "desc": "删除此项目", "function": this.removeItem},
        {"name": "U", "desc": "转为紧急任务", "function": this.toUrgentTask},
        {"name": "T", "desc": "转为今日任务", "function": this.toTodayTask},
        {"name": "E", "desc": "增加预计时间", "function": this.increaseExpectedTomatoTime},
      ]
    }
  },
  created() {
    this.reload();
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
    },
    reload: function () {
      this.axios.post("/item/getAll", {"parent": this.parent}).then(res => {
        console.log(res.data.data)
        this.todayTask = res.data.data.todayTask
        this.urgentTask = res.data.data.urgentTask
        this.activeTask = res.data.data.activeTask
      })
    },
    backItem: function (index, id) {
      this.axios.post("/item/back", {"id": id, "parent": this.parent}).then(res => {
        this.findItem(index, id).splice(index, 1)
        this.activeTask = res.data.data
      })
    },
    removeItem: function (index, id) {
      this.axios.post("/item/remove", {"id": id}).then(() => this.findItem(index, id).splice(index, 1))
    },
    increaseExpectedTomatoTime: function (index, id) {
      this.axios.post("/item/increaseExpectedTomatoTime", {"id": id}).then(() => this.findItem(index, id)[index].expected_tomato += 1)
    },
    increaseUsedTomatoTime: function (index, id) {
      this.axios.post("/item/increaseUsedTomatoTime", {"id": id}).then(() => this.findItem(index, id)[index].used_tomato += 1)
    },
    startTomatoTimer: function (index, id) {
      this.axios.post("/tomato/setTask", {"id": id}).then(() => window.open("/home/tomato"))
    },
    toUrgentTask: function (index, id) {
      this.axios.post("/item/toUrgentTask", {"id": id}).then(() => {
        let item = this.activeTask[index]
        this.activeTask.splice(index, 1)
        this.urgentTask.push(item)
      })
    },
    toTodayTask: function (index, id) {
      console.log([index, id])
      this.axios.post("/item/toTodayTask", {"id": id}).then(() => {
        let item = this.activeTask[index]
        this.activeTask.splice(index, 1)
        this.todayTask.push(item)
      })
    },
    finishTask: function (index, id) {
      this.increaseUsedTomatoTime(index, id)
    },
    checkUpdateStatus: function () {
      const today = new Date().getDate();
      if (today !== this.lastUpdateDate) {
        console.log("Update State!")
        this.reload();
        this.lastUpdateDate = today;
      }
    }
  },
  mounted() {
    window.onfocus = this.checkUpdateStatus
  },
  watch: {
    "updateTodo": function () {
      this.axios.post("/item/getActivate", {"parent": this.parent}).then(res => this.activeTask = res.data.data);
    },
    "createPlaceHold": function () {
      this.todayTask.unshift({
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
      })
    }
  }
}


</script>

<style scoped>

</style>