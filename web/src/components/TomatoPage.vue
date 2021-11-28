<template>
  <div style="height: 500px">
    <p style="text-align:center;font-size: 45px">{{ timeWithMin }}</p>
    <button style="display:block;margin:0 auto;font-size: 25px;" @click="reset">重置番茄钟</button>
  </div>
</template>

<script>

const resetTime = 5 * 60;
const tomatoTime = 25 * 60;

export default {
  name: "TomatoPage",
  data: function () {
    return {
      timeSeconds: 0,
      stage: "FOCUS",
    }
  },
  mounted() {
    this.reset()
    setInterval(this.timeHandler, 1000)
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
      if (this.stage === "FOCUS") {
        if (this.timeSeconds > 0) {
          this.timeSeconds -= 1
        } else {
          this.stage = "REST"
          this.timeSeconds = resetTime;
          new Notification("专注时间结束", {body: "完成一个番茄钟了, 休息一下吧~"})
        }
      } else if (this.stage === "REST") {
        if (this.timeSeconds > 0) {
          this.timeSeconds -= 1;
        } else {
          this.stage = "DONE"
          new Notification("休息结束", {body: ""})
        }
      }
    },
    reset: function () {
      this.stage = "FOCUS"
      this.timeSeconds = tomatoTime
    }
  }
}


</script>

<style scoped>

</style>