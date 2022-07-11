<template>
  <!-- 弹出的提示框, 指示是否保存成功 -->
  <div id="alert" class="alert-show" v-show="show">{{ text }}</div>
</template>

<script>
export default {
  name: "Alert",
  props: {
    text: String,
    show: Boolean,
  },
  data: function () {
    return {}
  }
}
</script>

<style scoped>
.alert-show {
  position: fixed;
  top: 50%;
  left: 50%;
  margin-left: -57px;
  padding: 8px 24px 8px 24px;
  color: #3c763d;
  background-color: #dff0d8;
  border: 1px solid transparent;
  border-radius: 4px;
  z-index: 99;
}
</style>