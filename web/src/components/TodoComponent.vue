<template>
  <div>
    <item-list title="正在进行" btn-name="↓" :data="todo" :done="false" @checkbox-change="finishTodoItem"
               @btn-click="promotion"></item-list>
    <item-list title="已经完成" btn-name="-" :data="done" :done="true" @checkbox-change="resetTodoItem"
               @btn-click="removeDone"></item-list>
    <item-list title="长期任务" btn-name="-" :data="old" :done="false" @btn-click="removeOld"></item-list>
  </div>
</template>

<script>
import ItemList from "@/components/list/ItemList";

export default {
  name: "TodoComponent",
  components: {ItemList},
  props: {
    updateTodo: Number,
    createPlaceHold: Number
  },
  data: function () {
    return {
      done: [],
      todo: [],
      old: []
    }
  },
  created() {
    this.$axios.post("/item/getAll").then(res => {
      this.todo = res.data.data.todo
      this.done = res.data.data.done
      this.old = res.data.data.old
    })
  },
  methods: {
    finishTodoItem: function (index) {
      this.$axios.post("/item/done", {"id": this.todo[index].id}).then(res => {
        this.done.unshift(this.todo[index]);
        this.todo = res.data.data;
      });
    },
    resetTodoItem: function (index) {
      this.$axios.post("/item/undone", {"id": this.done[index].id}).then(res => {
        this.done.splice(index, 1);
        this.todo = res.data.data;
      });
    },
    removeDone: function (index) {
      this.$axios.post("/item/remove", {"id": this.done[index].id})
          .then(() => this.done.splice(index, 1));
    },
    removeOld: function (index) {
      this.$axios.post("/item/remove", {"id": this.old[index].id})
          .then(() => this.old.splice(index, 1));
    },
    promotion: function (index) {
      this.$axios.post("/item/toOld", {"id": this.todo[index].id}).then(() => {
        this.old.unshift(this.todo[index]);
        this.todo.splice(index, 1);
      });
    },
  },
  watch: {
    "updateTodo": function () {
      this.$axios.post("/item/getTodo").then(res => this.todo = res.data.data);
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


</script>

<style scoped>

</style>