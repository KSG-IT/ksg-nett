
const semesterEl = document.querySelector(".summariestypedetail__currentsemester")
const semesterSelectEl = document.querySelector(".summariestypedetail__semesterselect")

semesterEl.addEventListener('click', () => {
    semesterSelectEl.classList.toggle("active")
})
