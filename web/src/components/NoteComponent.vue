<template>
  <div>
    <!-- 主体：文本编辑器控制按钮 -->
    <div id='editControls' class='span12' style='text-align:center; padding:5px;'>
      <div class='btn-group'>
        <a class='btn' data-role='h1' href='#'>h<sup>1</sup></a>
        <a class='btn' data-role='h2' href='#'>h<sup>2</sup></a>
        <a class='btn' data-role='p' href='#'>p</a>
        <a class='btn' data-role='bold' href='#'><b>Bold</b></a>
        <a class='btn' data-role='italic' href='#'><em>Italic</em></a>
        <a class='btn' data-role='underline' href='#'><u><b>U</b></u></a>
        <a class='btn' data-role='strikeThrough' href='#'>
          <del>abc</del>
        </a>
        <a class='btn' data-role='undo' href='#'>Undo</a>
        <a class='btn' data-role='redo' href='#'>Redo</a>
      </div>
    </div>

    <item-list title="正在进行" btn-name="-" :data="todo" :done="false" @checkbox-change="finishTodoItem"
               @btn-click="removeTodo"></item-list>

    <!-- 主体：文本编辑器 -->
    <div id='editor' class='span12' style='' contenteditable="true">
      <span v-html="content"/>
    </div>


    <item-list title="已经完成" btn-name="-" :data="done" :done="true" @checkbox-change="resetTodoItem"
               @btn-click="removeDone"></item-list>


    <!-- 弹出的提示框, 指示是否保存成功 -->
    <div id="alert" class="alert-none">保存成功</div>

  </div>


</template>

<script>

import ItemList from "@/components/list/ItemList";

export default {
  name: "NoteComponent",
  components: {ItemList},
  props: {
    updateTodo: Number
  },
  data: function () {
    return {
      done: [],
      todo: [],
      old: [],
      content: "",
      lastContent: undefined
    }
  },
  created() {
    // 获取Note私有的Item列表
    this.$axios.post("/note/getAll", {"id": this.$route.params.id}).then(res => {
      this.todo = res.data.data.todo
      this.done = res.data.data.done
      this.old = res.data.data.old
    });

    // 获取note的正文内容
    this.$axios.post("/note/content", {"id": this.$route.params.id})
        .then(res => this.content = res.data.data)

    //绑定保存按键
    document.onkeydown = this.save;

    // 设置自动保存
    setInterval(() => {
      const currentHTML = document.getElementById("editor").innerHTML;
      if (currentHTML !== this.lastContent) {
        console.log(["autoSave", currentHTML])
        this.lastContent = currentHTML
        this.$axios.post("note/update", {
          "id": this.$route.params.id,
          "content": currentHTML
        });
      }
    }, 60 * 1000)

  },
  methods: {
    finishTodoItem: function (index) {
      this.$axios.post("/item/done", {
        "id": this.todo[index].id,
        "parent": this.$route.params.id
      }).then(res => {
        this.done.unshift(this.todo[index]);
        this.todo = res.data.data;
      });
    },
    resetTodoItem: function (index) {
      this.$axios.post("/item/undone", {
        "id": this.done[index].id,
        "parent": this.$route.params.id
      }).then(res => {
        this.done.splice(index, 1);
        this.todo = res.data.data;
      });
    },
    removeTodo: function (index) {
      this.$axios.post("/item/remove", {
        "id": this.todo[index].id,
        "parent": this.$route.params.id
      }).then(() => this.todo.splice(index, 1));
    },
    removeDone: function (index) {
      this.$axios.post("/item/remove", {
        "id": this.done[index].id,
        "parent": this.$route.params.id
      }).then(() => this.done.splice(index, 1));
    },

    save: function (event) {
      // Ctrl + S
      if (event.ctrlKey && event.keyCode === 83) {
        event.preventDefault();

        this.$axios.post("note/update", {
          "id": this.$route.params.id,
          "content": document.getElementById("editor").innerHTML
        }).then(() => {
          showAlert();
          setTimeout(hideAlert, 500);
        });
      }
    },
  },
  watch: {
    "updateTodo": function () {
      this.$axios.post("/note/getTodo", {"id": this.$route.params.id})
          .then(res => this.todo = res.data.data);
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
.btn-group > a {
  position: relative;
  display: inline-flex;
  vertical-align: middle;
  margin-left: 8px;
}

.btn-group > .btn {
  position: relative;
  flex: 1 1 auto;
}

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
  position: absolute;
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