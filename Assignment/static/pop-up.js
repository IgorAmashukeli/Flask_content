let popup = document.getElementById("PopUp");
let items = document.querySelectorAll("*");
let After = document.getElementById("After");

function OpenPopup() {
  items.forEach((item) => {
    item.classList.add("background-adding");
  });
  After.hidden = true;
  popup.classList.add("openPopUp");
}

function ClosePopup() {
  items.forEach((item) => {
    item.classList.remove("background-adding");
  });
  After.hidden = false;
  popup.classList.remove("openPopUp");
}
