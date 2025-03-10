let few = document.getElementById("few");
let all = document.getElementById("all");
let expand = document.getElementById("expand");
let close_com = document.getElementById("close_com");


function Expand() {
    few.hidden = true;
    expand.hidden = true;
    all.hidden = false;
    close_com.hidden = false;
}


function CloseCom() {
    few.hidden = false;
    expand.hidden = false;
    all.hidden = true;
    close_com.hidden = true;
}