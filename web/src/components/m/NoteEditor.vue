<template>
  <div id='editor' contenteditable="true" @keydown.tab="tab" @keydown="hotKeyDispatcher" @input="this.$emit('changed')"
       v-html="initContent"></div>
</template>

<script>
export default {
  name: "NoteEditor",
  props: {
    initContent: String,
  },
  data: function () {
    return {
      contentUpdated: false,  // 指示前端是否修改了content内容
    }
  },
  mounted() {

  },
  methods: {
    hotKeyDispatcher: function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        this.save()
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault()
        this.doAction('bold')
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
        e.preventDefault()
        this.doAction('italic')
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
        e.preventDefault()
        this.doAction('underline')
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
        e.preventDefault()
        this.doAction('strikeThrough')
      } else if ((e.ctrlKey || e.metaKey) && e.key === '1') {
        e.preventDefault()
        this.doAction('h1')
      } else if ((e.ctrlKey || e.metaKey) && e.key === '2') {
        e.preventDefault()
        this.doAction('h2')
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'h') {
        e.preventDefault()
        this.line(e)
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'o') {
        e.preventDefault()
        this.note(e)
      }
    },
    doAction: function (role) {
      const baseAction = ['h1', 'h2', 'p'];

      if (baseAction.indexOf(role) !== -1) {
        document.execCommand('formatBlock', false, '<' + role + '>');
      } else {
        document.execCommand(role, false, null);
      }
    },
    save: function () {
      this.$emit("save", document.getElementById("editor").innerHTML)
    },
    tab: function (event) {
      this.insertHTML(event, '&nbsp;&nbsp;&nbsp;&nbsp;')
    },
    line: function (event) {
      this.insertHTML(event, '<hr />')
    },
    note: function (event) {
      this.insertHTML(event, '<blockquote class="quote"><b>Note</b>:</blockquote>')
    },
    insertHTML: function (event, content) {
      // 阻止默认切换元素的行为
      if (event && event.preventDefault) {
        event.preventDefault()
      } else {
        window.event.returnValue = false
      }
      // 获取光标的range对象 event.view 是一个window对象
      let range = event.view.getSelection().getRangeAt(0);
      // 光标的偏移位置
      let offset = range.startOffset;
      // 新建一个span元素
      let span = document.createElement('span');
      // 插入给定的内容
      span.innerHTML = content;
      // 创建一个新的range对象
      let newRange = document.createRange();
      // 设置新的range的位置，也是插入元素的位置
      newRange.setStart(range.startContainer, offset);
      newRange.setEnd(range.startContainer, offset);
      newRange.collapse(true);
      newRange.insertNode(span);
      // 去掉旧的range对象，用新的range对象替换
      event.view.getSelection().removeAllRanges();
      event.view.getSelection().addRange(range);
      // 将光标的位置向后移动一个偏移量，放到加入的四个空格后面
      range.setStart(span, 1);
      range.setEnd(span, 1);
    }
  }


}
</script>

<style>


#editor {
  resize: vertical;
  overflow: auto;
  border: 1px solid silver;
  border-radius: 5px;
  min-height: 100px;
  box-shadow: inset 0 0 10px silver;
  padding: 1em;
}

blockquote {
  position: relative;
  padding: 1px 5px;
  border-left: 4px solid #3d89db;
  /*color: #6e6e6e;*/
  background: #d2d2d2;
  /*font-size: 14px;*/
  border-radius: 0 2px 2px 0;
  margin: 0 0;
}


</style>