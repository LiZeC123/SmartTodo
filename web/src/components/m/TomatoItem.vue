<template>
  <div>
    <h2 v-show="show">当前任务</h2>
    <ol v-show="show">
      <audio id="notificationAudio" :src="auditSrc"></audio>
      <li :class="stage" :title="desc">【{{ timeWithMin }}】{{ taskName }}
        <a class="function function-1" title="取消任务" @click="cancelTask">
          <font-awesome-icon :icon="['fas', 'undo']"/>
        </a>
        <a class="function function-0" title="完成任务" @click="finishTask">
          <font-awesome-icon :icon="['fas', 'check']"/>
        </a>
      </li>
    </ol>
  </div>
</template>

<script>

import OceanWaves from "@/assets/OceanWaves.mp3";
const OneMinuteMS = 60 * 1000

export default {
  name: "TomatoPage",
  emits: ['done-task'],
  props: {
    reloadCount: Number,
  },
  data: function () {
    return {
      startTime: new Date(),
      taskId: 0,
      seqId: 0,
      taskName: "任务名",
      timeSeconds: 0,
      stage: "DONE",
      habit: false,
      hasShowFocusMessage: false,
      auditSrc: OceanWaves,
    }
  },
  mounted() {
    setInterval(this.updateTimeSecond, 500)
    this.reload(false)
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
    },
    desc: function () {
      return "开始时间:" + this.startTime.toLocaleTimeString() + "\n" +
          "当前状态" + this.stage;
    },
    show: function () {
      return this.taskId !== 0
    },
  },
  methods: {
    reload: function () {
      this.axios.get("/tomato/getTask").then(res => {
        const d = res.data
        const tsStart = d.start * 1000


        this.startTime = new Date(tsStart)
        this.taskName = d.name
        this.taskId = d.id
        this.seqId = d.tid
        this.hasShowFocusMessage = d.finished
        this.habit = d.habit

        console.log(res.data ,tsStart, this.startTime)

        this.updateTimeSecond()
      })
    },
    updateTimeSecond: function () {
      if (!this.habit) {
        this.updateTomato()
      } else {
        this.updateHabit()
      }
    },
    updateTomato: function () {
      let tsNow = new Date().getTime()
      let elapsedMs = tsNow - this.startTime

      // 没有任务的情况
      if (this.taskId === 0) {
        this.stage = "DONE"
        this.timeSeconds = 0
        return;
      }

      const tomatoTimeMS = this.$store.state.tomatoTime * OneMinuteMS
      // 不超过一个番茄钟时间, 直接设置状态并返回
      if (elapsedMs < tomatoTimeMS) {
        this.stage = "FOCUS"
        this.timeSeconds = Math.floor((tomatoTimeMS - elapsedMs) / 1000)
        return;
      }

      // 此函数周期性调用, 但只需要发送一次完成任务请求
      if (this.hasShowFocusMessage === false) {
        this.finishTask()
      }

      // 超过休息时间, 清除任务
      this.stage = "DONE"
      this.timeSeconds = 0
    },
    updateHabit: function () {
      const tsStart = this.startTime
      let tsNow = new Date().getTime()
      this.timeSeconds = (tsNow - tsStart) / 1000

      this.stage = "FOCUS"
    },
    bodyMessage: function () {
      return "任务: " + this.taskName;
    },
    param: function () {
      return {"tid": this.seqId, "id": this.taskId}
    },
    cancelTask: function () {
      this.axios.post("/tomato/undoTask", this.param()).then(() => {
        this.$emit('done-task', "undo")
        this.reload()
      })
    },
    finishTask: function () {
      this.axios.post("/tomato/finishTaskManually", this.param()).then(res => {
        let isSuccess = res.data
        if (isSuccess) {
          new Notification("完成一个番茄钟了, 休息一下吧~", {body: this.bodyMessage()})
          this.playNotifacationAudio()
        }

        this.$emit('done-task', "done", this.taskId)
        this.reload()
      })
    },
    playNotifacationAudio() {
      let audio = document.getElementById("notificationAudio")
      audio.loop = true
      audio.play()
      setTimeout(()=> audio.pause(), OneMinuteMS)
    }
  },
  watch: {
    "reloadCount": function () {
      this.reload()
    }
  }
}


</script>

<style scoped>
/*清除ol和ul标签的默认样式*/
ol, ul {
  padding: 0;
  list-style: none;
}

.FOCUS {
  border-left: 5px solid #EE0000;
  line-height: 32px;
  background: #fff;
  position: relative;
  margin-bottom: 10px;
  padding: 0 88px 0 8px;
  border-radius: 3px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.07);
}

.DONE {
  border-left: 5px solid #999;
  /*不透明度 0完全透明~1完全不透明*/
  opacity: 0.5;
  /*删除线效果*/
  text-decoration: line-through;
  line-height: 32px;
  background: #fff;
  position: relative;
  margin-bottom: 10px;
  padding: 0 88px 0 8px;
  border-radius: 3px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.07);
}


.function {
  position: absolute;
  display: inline-block;
  width: 14px;
  height: 12px;
  line-height: 14px;
  text-align: center;
  color: #888;
  font-weight: bold;
  font-size: 20px;
  cursor: pointer;
}

.function-0 {
  top: 6px;
  right: 14px;
}

.function-1 {
  top: 6px;
  right: 44px;
}
</style>