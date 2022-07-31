<template>
  <div>
    <h2>{{ title }}</h2>
    <message-box :message="content" ></message-box>
  </div>
</template>

<script>
import MessageBox from "@/components/m/MessageBox";
export default {
  name: "LogTypeComponent",
  components: {MessageBox},
  data: function () {
    return {
      title: "",
      content: "",
    }
  },
  created() {
    let type = this.$route.params.type;
    switch (type) {
      case "data":
        this.title = "用户数据";
        break;
      case "log":
        this.title = "系统日志";
        break
      default:
        console.warn("无效的类型");
        this.title = "数据";
    }
    document.title = this.title;
    this.axios.get("/log/" + type).then(rep => this.content = rep.data);
  }
}
</script>

<style scoped>

</style>