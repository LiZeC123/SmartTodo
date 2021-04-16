<template>
  <div>Hello, Current Nid =  {{ nid }}</div>
</template>

<script>
export default {
  name: "NoteComponent",
  data: function () {
    return {
      nid: this.$route.params.nid
    }
  },
}
</script>

<style scoped>

</style>