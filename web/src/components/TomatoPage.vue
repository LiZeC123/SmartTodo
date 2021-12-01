<template>
  <div style="height: 500px">
    <p>开始时间: {{ startTime.toLocaleTimeString() }} </p>
    <p>任务名称: {{ taskName }}</p>
    <p>当前状态: {{ stage }}</p>
    <p style="text-align:center;font-size: 45px">{{ timeWithMin }}</p>
    <div style="display:block;margin:auto;font-size: 25px;position: absolute;">
      <button @click="undoTask">取消任务</button>
      <button @click="finishTask">提前完成</button>
    </div>
  </div>
</template>

<script>

const resetTime = 5 * 60
const tomatoTime = 25 * 60

const resetTimeMS = 1000 * resetTime
const tomatoTomeMS = 1000 * tomatoTime

export default {
  name: "TomatoPage",
  data: function () {
    return {
      startTime: new Date(),
      taskId: 0,
      taskName: "任务名",
      timeSeconds: 0,
      stage: "DONE",
      hasShowFocusMessage: false,
      hasShowRestMessage: false,
    }
  },
  mounted() {
    setInterval(this.timeHandler, 500)

    document.title = "番茄钟"

    this.axios.get("/tomato/getTask").then(res => {
      console.log(res.data.data)
      let d = res.data.data
      let tsStart = d.startTime * 1000

      this.updateTimeSecond(tsStart)

      this.startTime = new Date(tsStart)
      this.taskName = d.name
      this.taskId = d.id
    })
  },
  computed: {
    timeWithMin: function () {
      if (this.timeSeconds < 0) {
        return "00:00"
      }

      let m = Math.floor(this.timeSeconds / 60);
      let s = Math.floor(this.timeSeconds % 60);
      if (m < 10) {
        m = "0" + m;
      }
      if (s < 10) {
        s = "0" + s;
      }
      return m + ":" + s;
    }
  },
  methods: {
    timeHandler: function () {
      // 注意: 每一秒钟此函数都会触发一次, 注意妥善处理后续情况

      this.updateTimeSecond(this.startTime)
      if (this.stage === "FOCUS" && this.timeSeconds === 0 && !this.hasShowFocusMessage) {
        new Notification("完成一个番茄钟了, 休息一下吧~", {body: "任务: " + this.taskName})
        this.hasShowFocusMessage = true
        this.finishTask()
      } else if (this.stage === "REST" && this.timeSeconds === 0 && !this.hasShowRestMessage) {
        new Notification("休息结束", {body: ""})
        this.hasShowRestMessage = true;
      }
    },
    updateTimeSecond: function (tsStart) {
      let tsNow = new Date().getTime()
      let delta = tsNow - tsStart
      if (delta < tomatoTomeMS) {
        this.stage = "FOCUS"
        this.timeSeconds = Math.floor((tomatoTomeMS - delta) / 1000)
      } else if (delta < tomatoTomeMS + resetTimeMS) {
        this.stage = "REST"
        this.timeSeconds = Math.floor((tomatoTomeMS + resetTimeMS - delta) / 1000)
      } else {
        this.stage = "DONE"
        this.timeSeconds = 0
      }
    },
    undoTask: function () {
      this.axios.post("/tomato/undoTask", {"id": this.taskId}).then(() => window.close())
    },
    finishTask: function () {
      this.axios.post("/tomato/finishTask", {"id": this.taskId})
    }
  }
}


</script>

<style scoped>

</style>