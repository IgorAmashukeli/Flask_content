var n = 50;
for (var i = 0; i < n; i++) {
    let few = document.getElementById("few" + i);
    let all = document.getElementById("all" + i);
    let expand = document.getElementById("expand" + i);
    let close_com = document.getElementById("close_com" + i);
    document.getElementById('expand' + i).addEventListener('click', function () {
        few.hidden = true;
        expand.hidden = true;
        all.hidden = false;
        close_com.hidden = false;
    });
    document.getElementById('close_com' + i).addEventListener('click', function () {
        few.hidden = false;
        expand.hidden = false;
        all.hidden = true;
        close_com.hidden = true;
    });
}