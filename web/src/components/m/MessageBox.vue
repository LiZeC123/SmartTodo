<template>
  <div>
    <!-- 弹出的提示框, 指示是否保存成功 -->
    <alert :text="'文本已复制'" :show="showAlert"></alert>
    <!--pre标签能够使文本中的换行符号正确的渲染-->
    <pre class="messageBox" @contextmenu.prevent @mousedown="click($event)"> {{ message }}</pre>
  </div>
</template>

<script>
import Alert from "@/components/m/Alert";
export default {
  name: "MessageBox",
  components: {Alert},
  props: {
    message: String,
  },
  data: function () {
    return {
      showAlert: false,
    }
  },
  methods: {
    click: function (event) {
      if (event.button === 2) {

        navigator.clipboard.writeText(this.message).then(() => {
          this.showAlert = true
          setTimeout(() => this.showAlert = false, 500);
        })
      }

    }
  }
}
</script>

<style scoped>

.messageBox {
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