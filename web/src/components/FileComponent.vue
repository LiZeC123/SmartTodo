<template>
  <div>
    <item-list title="公共空间" btn-name="-" :data="publicFiles" :done="false" @checkbox-change="refresh"
               @btn-click="remove"></item-list>

    <p style="margin: auto;text-align:center">公共空间的文件在24小时后自动删除</p>
  </div>
</template>

<script>
import ItemList from "@/components/list/ItemList";

export default {
  name: "FileComponent",
  components: {ItemList},
  props: {
    updateTodo: Number
  },
  data: function () {
    return {
      publicFiles: [],
    }
  },
  created() {
    this.axios.post("/file/getAll").then(res => this.publicFiles = res.data.data);
  },
  methods: {
    refresh: function () {
      console.warn("刷新功能不可用");
    },
    remove: function (index) {
      this.axios.post("/item/remove", {"id": this.publicFiles[index].id})
          .then(() => this.publicFiles.splice(index, 1));
    },
  },
  watch: {
    "updateTodo": function () {
      this.axios.post("/file/getAll").then(res => this.publicFiles = res.data.data);
    }
  }
}
</script>

<style scoped>

</style>