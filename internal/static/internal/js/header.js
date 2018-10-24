'use strict';


const headerBottomEl = document.querySelector(".header__bottom")
const headerMenuButtonEl = document.querySelector(".header__menu")

headerMenuButtonEl.addEventListener('click', function (event){
    headerBottomEl.classList.toggle("header__bottom--open");
});
