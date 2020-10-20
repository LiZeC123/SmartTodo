function save(nid, notShow) {
    const text = document.getElementById("editor").innerHTML;
    const data = {
        "nid": nid,
        "text": text
    };

    $.post("/smart-todo/note/update", data, function () {
        if (notShow !== true) {
            $('.alert').html('操作成功').addClass('alert-success').show().delay(500).fadeOut();
        }
    })
}

function autoSave(nid) {
    save(nid, true);
}

function updateTodo(data) {
    const tStr = "<li class='{type}' id='li-active'><input type='checkbox' onchange='update({id})' />" +
        "<p id='p-{id}' onclick='edit(\"{url}\")'>{showName}</p>";
    const dictFunc = function (item) {
        return {
            "type": item.itemType, "id": item.id,
            "url": item.url, "showName": item.showName,
        }
    };
    updateTemplate(data, document.getElementById("todoCount"),
        document.getElementById("todoList"), tStr, dictFunc);
}

function updateHTML(data) {
    updateTodo(fillShowName(data.todo));
    updateDone(fillShowName(data.done));
}

function fetchData(callBack) {
    const nid = /note\/(\d+)/.exec(document.URL)[1];
    $.post("/smart-todo/items/todo", {"nid": nid}, callBack);
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
            console.log("Auto Save")
        } else {
            console.log("Content Not Change")
        }
    }, 60 * 1000)
});