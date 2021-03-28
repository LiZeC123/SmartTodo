let vm = new Vue({
    el: "#todoContent",
    data: {
        done: [],
        todo: [],
        old: [],
        note: null
    },
    mounted() {
        const nid = /note\/(\d+)/.exec(document.URL)[1];
        reload(nid);
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


function reload() {
    const nid = /note\/(\d+)/.exec(document.URL)[1];
    axios.post("/items/todo",{"nid": nid}).then(response => {
        vm.todo = fillShowName(response.data.todo)
        vm.done = fillShowName(response.data.done)
        vm.old = fillShowName(response.data.old)
    });
}

function save(notShow) {
    const nid = /note\/(\d+)/.exec(document.URL)[1];
    const text = document.getElementById("editor").innerHTML;
    const data = {
        "nid": nid,
        "text": text
    };

    axios.post("/note/update", data).then(function () {
        if (notShow !== true) {
            $('.alert').html('操作成功').addClass('alert-success').show().delay(500).fadeOut();
        }
    })

}

function autoSave() {
    save(true);
}

$(function () {
    // 从URL获得NoteId
    const nid = /note\/(\d+)/.exec(document.URL)[1];

    let content = document.getElementById("editor").innerHTML;
    $('#editControls a').click(function () {
        switch ($(this).data('role')) {
            case 'h1':
            case 'h2':
            case 'p':
                document.execCommand('formatBlock', false, '<' + $(this).data('role') + '>');
                break;
            default:
                document.execCommand($(this).data('role'), false, null);
                break;
        }
    });

    $(document).keydown(function (event) {
        // Ctrl + S
        if (event.ctrlKey && event.keyCode === 83) {
            save(nid);
            event.preventDefault();
            content = document.getElementById("editor").innerHTML;
        }

    });

    setInterval(function () {
        const currentHTML = document.getElementById("editor").innerHTML;
        if (currentHTML !== content) {
            autoSave(nid);
            content = document.getElementById("editor").innerHTML;
        }
    }, 60 * 1000)
});