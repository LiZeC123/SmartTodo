<template>
  <div v-show="taskId !== 0">
    <h2>当前任务</h2>
    <ol>
      <li :class="stage" :title="desc">【{{ timeWithMin }}】{{ taskName }}
        <a class="function function-0" title="取消任务" @click="undoTask">R</a>
        <a class="function function-1" title="完成任务" @click="finishTask">D</a>
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
  props: {
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
      hasShowRestMessage: false,
    }
  },
  mounted() {
    setInterval(this.timeHandler, 500)
    this.reload()
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
    }
  },
  methods: {
    reload: function () {
      this.axios.get("/tomato/getTask").then(res => {
        let d = res.data.data
        let tsStart = d.startTime * 1000

        this.updateTimeSecond(tsStart)

        this.startTime = new Date(tsStart)
        this.taskName = d.name
        this.taskId = d.id
      })
    },
    timeHandler: function () {
      // 注意: 每一秒钟此函数都会触发一次, 需要处理时间的所有可能情况
      this.updateTimeSecond(this.startTime)
      if (this.stage === "FOCUS" && this.timeSeconds === 0 && !this.hasShowFocusMessage) {
        new Notification("完成一个番茄钟了, 休息一下吧~", {body: "任务: " + this.taskName})
        this.hasShowFocusMessage = true
      } else if (this.stage === "REST" && this.timeSeconds === 0 && !this.hasShowRestMessage) {
        new Notification("休息结束", {body: ""})
        this.hasShowRestMessage = true;
        this.finishTask()
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
      this.axios.post("/tomato/undoTask", {"id": this.taskId}).then(() => {
        this.$emit('done', "undo")
        this.taskId = 0
      })
    },
    finishTask: function () {
      this.axios.post("/tomato/finishTask", {"id": this.taskId}).then(() => {
        this.$emit('done', "done", this.taskId)
        this.taskId = 0
      })
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
  border-radius: 14px;
  border: 6px double #FFF;
  background: #CCC;
  line-height: 14px;
  text-align: center;
  color: #FFF;
  font-weight: bold;
  font-size: 14px;
  cursor: pointer;
}

.function-0 {
  top: 4px;
  right: 4px;
}

.function-1 {
  top: 4px;
  right: 34px;
}

</style>