<template>
  <div>
    <h2 v-show="show">当前任务</h2>
    <ol v-show="show">
      <li :class="stage" :title="desc">【{{ timeWithMin }}】{{ taskName }}
        <a class="function function-1" title="取消任务" @click="cancelTask">
          <font-awesome-icon :icon="['fas', 'undo']"/>
        </a>
        <a class="function function-0" title="提前完成任务" @click="forceFinishTask">
          <font-awesome-icon :icon="['fas', 'check']"/>
        </a>
      </li>
    </ol>
  </div>
</template>

<script>

const resetTime = 5 * 60
const tomatoTime = 25 * 60

const resetTimeMS = 1000 * resetTime
const tomatoTomeMS = 1000 * tomatoTime

export default {
  name: "TomatoPage",
  emits: ['done-task'],
  props: {
    resetCount: Number,
    reloadCount: Number,
  },
  data: function () {
    return {
      startTime: new Date(),
      taskId: 0,
      taskName: "任务名",
      timeSeconds: 0,
      stage: "DONE",
      hasShowFocusMessage: false,
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
        const tsStart = d.startTime * 1000

        this.startTime = new Date(tsStart)
        this.taskName = d.name
        this.taskId = d.id
        this.hasShowFocusMessage = d.finished

        this.updateTimeSecond()
      })
    },
    updateTimeSecond: function () {
      const tsStart = this.startTime
      let tsNow = new Date().getTime()
      let delta = tsNow - tsStart

      // 没有任务的情况
      if (this.taskId === 0) {
        this.stage = "DONE"
        this.timeSeconds = 0
        return;
      }

      // 不超过一个番茄钟时间, 直接设置状态并返回
      if (delta < tomatoTomeMS) {
        this.stage = "FOCUS"
        this.timeSeconds = Math.floor((tomatoTomeMS - delta) / 1000)
        return;
      }

      // 否则无论当前具体处于哪个状态, 都要先判定是否发送过消息
      if (this.hasShowFocusMessage === false) {
        this.finishTask()
      }

      // 不超过休息时间, 则正常设置休息状态并返回
      if (delta < tomatoTomeMS + resetTimeMS) {
        this.stage = "REST"
        this.timeSeconds = Math.floor((tomatoTomeMS + resetTimeMS - delta) / 1000)
        return;
      }

      // 超过休息时间, 清除任务
      this.clearTask()
      this.stage = "DONE"
      this.timeSeconds = 0
    },
    bodyMessage: function () {
      return "任务: " + this.taskName;
    },
    cancelTask: function () {
      this.axios.post("/tomato/undoTask", {"id": this.taskId}).then(() => {
        this.$emit('done-task', "undo")
        this.reload()
      })
    },
    forceFinishTask: function () {
      this.axios.post("/tomato/finishTaskManually", {"id": this.taskId}).then(() => {
        this.$emit('done-task', "done", this.taskId)
        this.reload()
      })
    },
    finishTask: function () {
      this.axios.post("/tomato/finishTask", {"id": this.taskId}).then(res => {
        let isSuccess = res.data
        if (isSuccess) {
          new Notification("完成一个番茄钟了, 休息一下吧~", {body: this.bodyMessage()})
        }

        this.$emit('done-task', "done", this.taskId)
        this.reload()
      })
    },
    clearTask: function () {
      this.axios.post("/tomato/clearTask", {"id": this.taskId}).then(res => {
        const isSuccess = res.data
        if(isSuccess) {
          new Notification("休息结束, 继续加油学习吧~", {body: this.bodyMessage()})
        }
        this.reload()
      })
    },
  },
  watch: {
    "resetCount": function () {
      this.reload()
    },
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

.REST {
  border-left: 5px solid #08bf02;
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