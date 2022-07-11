<template>
  <div>
    <!-- 主体：文本编辑器控制按钮 -->
    <todo-page :updateTodo="updateTodo" :createPlaceHold="createPlaceHold" :parent="parentId"></todo-page>

    <!-- 主体：文本编辑器 -->
    <div><span>{{ showSaveState }}</span> <span @click="save" style="float: right">保存文档</span></div>
    <note-editor :init-content="initContent" @save="save" @changed="updateContent"></note-editor>

    <!-- 弹出的提示框, 指示是否保存成功 -->
    <alert :text="'保存成功'" :show="showAlert"></alert>

  </div>


</template>

<script>
import NoteEditor from "@/components/m/NoteEditor"
import TodoPage from "@/components/TodoPage";
import Alert from "@/components/m/Alert";

export default {
  name: "NotePage",
  components: {Alert, TodoPage, NoteEditor},
  props: {
    updateTodo: Number,
    createPlaceHold: Number
  },
  data: function () {
    return {
      initContent: "",
      contentUpdated: false,  // 指示前端是否修改了content内容
      lastUpdateDate: new Date().getDate(),
      showAlert: false,
    }
  },
  created() {
    this.reload()
  },
  computed: {
    showSaveState: function () {
      if (this.contentUpdated) {
        return "文档已发生更改"
      } else {
        return "文档已保存"
      }
    },
    parentId: function () {
      if (typeof this.$route.params.id === "string") {
        return this.$route.params.id
      } else {
        return "0"
      }
    }
  },
  mounted() {
    // 关闭页面时如果未保存则执行保存操作
    window.onbeforeunload = this.checkUnsaved;

    // 设置自动保存
    setInterval(this.autoSave, 60 * 1000);
  },
  methods: {
    reload: function () {
      const data = {"id": this.$route.params.id}
      this.axios.post("/item/getTitle", data).then(res => document.title = res.data)
      this.axios.post("/note/content", data).then(res => this.initContent = res.data)
    },
    updateContent: function () {
      this.contentUpdated = true
    },
    save: function () {
      this.axios.post("note/update", {
        "id": this.$route.params.id,
        "content": document.getElementById("editor").innerHTML
      }).then(() => {
        this.contentUpdated = false
        this.showAlert = true
        setTimeout(() => this.showAlert = false, 500);
      });
    },
    autoSave: function () {
      if (this.contentUpdated) {
        console.log("autoSave")
        this.axios.post("note/update", {
          "id": this.$route.params.id,
          "content": document.getElementById("editor").innerHTML
        }).then(() => this.contentUpdated = false)
      }
    },
    checkUnsaved: function (e) {
      e.preventDefault();
      if (this.contentUpdated) {
        // 设置为false来弹窗阻止关闭
        e.returnValue = false;
      }
    },
  },
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
}


</style>