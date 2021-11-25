<template>
  <div>
    <!-- 主体：文本编辑器控制按钮 -->
    <item-list title="正在进行" btn-name="-" :data="todo" :done="false" @checkbox-change="finishTodoItem"
               @btn-click="removeTodo"></item-list>

    <!-- 主体：文本编辑器 -->
    <div><span>{{ showSaveState }}</span> <span @click="save" style="float: right">保存文档</span></div>
    <note-editor :init-content="initContent" @save="save" @changed="updateContent"></note-editor>

    <item-list title="已经完成" btn-name="-" :data="done" :done="true" @checkbox-change="resetTodoItem"
               @btn-click="removeDone"></item-list>


    <!-- 弹出的提示框, 指示是否保存成功 -->
    <div id="alert" class="alert-none">保存成功</div>

  </div>


</template>

<script>

import ItemList from "./list/ItemList";
import NoteEditor from "./NoteEditor";

export default {
  name: "NoteComponent",
  components: {NoteEditor, ItemList},
  props: {
    updateTodo: Number,
    createPlaceHold: Number
  },
  data: function () {
    return {
      done: [],
      todo: [],
      old: [],
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
    }
  },
  mounted() {
    // 获得焦点后自动更新一次
    window.onfocus = this.checkUpdateStatus
    // 关闭页面时如果未保存则执行保存操作
    window.onbeforeunload = this.checkUnsaved;

    // 设置自动保存
    setInterval(this.autoSave, 60 * 1000);
  },
  methods: {
    reload: function () {
      // 获取Note私有的Item列表
      this.reloadItem()

      // 获取Note的标题并设置为页面的标题
      this.axios.post("/item/getTitle", {"id": this.$route.params.id}).then(res => document.title = res.data.data);
      // 获取note的正文
      this.axios.post("/note/content", {"id": this.$route.params.id})
          .then(res => {
            this.initContent = res.data.data
          });
    },
    reloadItem: function () {
      this.axios.post("/note/getAll", {"id": this.$route.params.id}).then(res => {
        this.todo = res.data.data.todo
        this.done = res.data.data.done
        this.old = res.data.data.old
      });
    },
    finishTodoItem: function (index) {
      this.axios.post("/item/done", {
        "id": this.todo[index].id,
        "parent": this.$route.params.id
      }).then(res => {
        this.done.unshift(this.todo[index]);
        this.todo = res.data.data;
      });
    },
    resetTodoItem: function (index) {
      this.axios.post("/item/undone", {
        "id": this.done[index].id,
        "parent": this.$route.params.id
      }).then(res => {
        this.done.splice(index, 1);
        this.todo = res.data.data;
      });
    },
    removeTodo: function (index) {
      this.axios.post("/item/remove", {
        "id": this.todo[index].id,
        "parent": this.$route.params.id
      }).then(() => this.todo.splice(index, 1));
    },
    removeDone: function (index) {
      this.axios.post("/item/remove", {
        "id": this.done[index].id,
        "parent": this.$route.params.id
      }).then(() => this.done.splice(index, 1));
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
    checkUpdateStatus: function () {
      const today = new Date().getDate();
      if (today !== this.lastUpdateDate) {
        console.log("Update State!")
        this.reloadItem();
        this.lastUpdateDate = today;
      }
    },
  },
  watch: {
    "updateTodo": function () {
      this.axios.post("/note/getTodo", {"id": this.$route.params.id})
          .then(res => this.todo = res.data.data);
    },
    "createPlaceHold": function () {
      this.todo.unshift({
        "id": 1,
        "name": "文件正在下载,请稍等...",
        "item_type": "file",
        "urgent": 0,
        "deadline": null,
        "old": false,
        "repeatable": false,
        "specific": 0,
        "work": false,
        "url": "#",
      })
    }
  }
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