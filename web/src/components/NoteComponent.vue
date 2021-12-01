<template>
  <div>
    <!-- 主体：文本编辑器控制按钮 -->
    <todo-component :updateTodo="updateTodo" :createPlaceHold="createPlaceHold" :parent="parentId"></todo-component>

    <!-- 主体：文本编辑器 -->
    <div><span>{{ showSaveState }}</span> <span @click="save" style="float: right">保存文档</span></div>
    <note-editor :init-content="initContent" @save="save" @changed="updateContent"></note-editor>

    <!-- 弹出的提示框, 指示是否保存成功 -->
    <div id="alert" class="alert-none">保存成功</div>

  </div>


</template>

<script>
import NoteEditor from "./NoteEditor";
import TodoComponent from "./TodoComponent";

export default {
  name: "NoteComponent",
  components: {TodoComponent, NoteEditor},
  props: {
    updateTodo: Number,
    createPlaceHold: Number
  },
  data: function () {
    return {
      initContent: "",
      contentUpdated: false,  // 指示前端是否修改了content内容
      lastUpdateDate: new Date().getDate()
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
    // // 获得焦点后自动更新一次
    // window.onfocus = this.checkUpdateStatus
    // 关闭页面时如果未保存则执行保存操作
    window.onbeforeunload = this.checkUnsaved;

    // 设置自动保存
    setInterval(this.autoSave, 60 * 1000);
  },
  methods: {
    reload: function () {
      // 获取Note的标题并设置为页面的标题
      this.axios.post("/item/getTitle", {"id": this.$route.params.id}).then(res => document.title = res.data.data);
      // 获取note的正文
      this.axios.post("/note/content", {"id": this.$route.params.id}).then(res => {
        this.initContent = res.data.data
      });
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
        showAlert();
        setTimeout(hideAlert, 500);
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

function showAlert() {
  document.getElementById("alert").className = 'alert-show';
}

function hideAlert() {
  document.getElementById("alert").className = 'alert-none';
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


.alert-none {
  display: none;
}

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
}
</style>