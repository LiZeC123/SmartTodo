<template>
  <div>
    <h2>{{ title }}</h2>
    <textarea v-model="content" id="editor" disabled></textarea>
  </div>
</template>

<script>
export default {
  name: "LogTypeComponent",
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
    this.axios.get("/log/" + type).then(rep => this.content = rep.data.data);
  }
}
</script>

<style scoped>

#editor {
  resize: vertical;
  overflow: auto;
  border: 1px solid silver;
  border-radius: 5px;
  min-height: 100px;
  box-shadow: inset 0 0 10px silver;
  padding: 1em;
  width: 1000px;
  height: 600px;
  margin-top: 16px;
}
</style>