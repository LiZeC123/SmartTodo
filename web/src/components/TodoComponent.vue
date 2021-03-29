<template>
  <div>
    <item-list title="正在进行" btn-name="↓" :data="todo" :done="false" @checkbox-change="finishTodoItem" @btn-click="empty"></item-list>
    <item-list title="已经完成" btn-name="-" :data="done" @checkbox-change="resetTodoItem" @btn-click="remove"></item-list>
    <item-list title="长期任务" btn-name="-" :data="old" :done="false" @checkbox-change="empty" @btn-click="remove"></item-list>
  </div>
</template>

<script>
import ItemList from "@/components/list/ItemList";

export default {
  name: "TodoComponent",
  components: {ItemList},
  data: function () {
    return {
      done: [{"id": 78, "name": "CS 224N  | Project", "itemType": "single", "createTime": "2020-02-13 14:19:25", "finishTime": null, "autoPriority": null, "urgent": -1, "deadline": null, "old": false, "repeatable": false, "specific": 0, "work": false, "url": "https://web.stanford.edu/class/cs224n/project.html", "parent": null}],
      todo: [{"id": 78, "name": "CS 224N  | Project", "itemType": "single", "createTime": "2020-02-13 14:19:25", "finishTime": null, "autoPriority": null, "urgent": -1, "deadline": null, "old": false, "repeatable": false, "specific": 0, "work": false, "url": "https://web.stanford.edu/class/cs224n/project.html", "parent": null}],
      old: [{"id": 78, "name": "CS 224N  | Project", "itemType": "single", "createTime": "2020-02-13 14:19:25", "finishTime": null, "autoPriority": null, "urgent": -1, "deadline": null, "old": false, "repeatable": false, "specific": 0, "work": false, "url": "https://web.stanford.edu/class/cs224n/project.html", "parent": null}]
    }
  },
  created() {

  },
  methods: {
    finishTodoItem: function (id) {
      //TODO: 向服务器发送请求, 收到回应后, 操作两个集合, 从而实现数据更新
      // 完成操作不需要排序, 但撤销操作需要排序, 因此可以部分的减少查询量
      // 删除操作直接删除, 因此也不需要再查询整个列表
      // 提升操作同理, 不需要进行排序
      // 添加操作需要排序, 但只需要更新todo部分
      console.log(id);
    },
    resetTodoItem: function (id) {
      console.log(id);
    },
    remove: function (id) {
      console.log(id);
    },
    promotion: function (id) {
      console.log(id);
    },
    empty: function () {

    }
  }
}
</script>

<style scoped>

</style>