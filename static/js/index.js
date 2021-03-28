let vm = new Vue({
    el: "#todoContent",
    data: {
        done: [],
        todo: [],
        old: []
    },
    created() {
        reload();
    },
    computed: {},
    methods: {
        update: id => axios.post("/item/update", {"id": id}).then(reload),
        remove: id => axios.post("/item/remove", {"id": id}).then(reload),
        promotion: id => axios.post("/item/old", {"id": id}).then(reload),
        jumpTo: url => {
            if (url !== null) {
                window.open(url)
            }
        }
    },
})