<template>
  <div>
    <h2>项目配置</h2>
    <div>
      <span>番茄钟时长</span>
      <select v-model="tomatoTime" style="width: 120px; margin-left: 20px">
        <option value="25">25分钟</option>
        <option value="30">30分钟</option>
        <option value="35">35分钟</option>
      </select>
    </div>
  </div>
</template>

<script>
export default {
  name: "Config",
  computed: {
    tomatoTime: {
      get () {
        return this.$store.state.tomatoTime;
      },
      set (newTime) {
        this.$store.commit('set_tomato_time', newTime);
      }
    }
  }
}
</script>

<style scoped>

</style>