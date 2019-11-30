/* global ace, createDelay, showdown, copyContentsToClipboard */


// Find original contents, in case we want to discard the draft
const summaryContents = document.querySelector('meta[name="summary-create-contents"]').getAttribute("content")

// This variable is used to save temporary edits to the local storage.
const localStorageSummariesContentKey = 'summaries-create-contents'

// Get references to some of the essential elements
const previewEl = document.getElementById("summarycreate-preview")
const contentsInputEl = document.getElementById("summarycreate-contentsinput")
const submitEl = document.getElementById("summarycreate-submit")
const formEl = document.getElementById("summarycreate-form")

// We use the delay-wrapper to delay updating our preview until a batch of inputs
// have finished (we use 500 ms to separate the batches)
const delayWrapper = createDelay()
const delayPeriod = 500  // ms

// Set up editor
const editor = ace.edit("summarycreate-contents", {
    mode: 'ace/mode/markdown',
    selectionStyle: 'text'
})
editor.setTheme('ace/theme/tomorrow')
editor.container.style.lineHeight = 1.5

// Set up rendering of markdown content
const showdownConverter = new showdown.Converter({
    extensions: ['highlight']
})
showdownConverter.setOption('simpleLineBreaks', true)
function onContentsUpdated(contents){
    // Save in localstorage
    localStorage.setItem(localStorageSummariesContentKey, contents)
    previewEl.innerHTML = showdownConverter.makeHtml(contents)
    contentsInputEl.value = contents
}

editor.on('change', function(e){
    delayWrapper(onContentsUpdated, delayPeriod, editor.getValue())
})

// Set up submission of form
submitEl.addEventListener('click', function(){
    // Remove data from local storage, as we are now sending the data to the server.
    // If the request fails somehow, the content should still be preserved, so we can safely delete here.
    localStorage.removeItem(localStorageSummariesContentKey)

    formEl.submit()
})

// If we have some saved content in localStorage, add it.
const localStorageSavedContent = localStorage.getItem(localStorageSummariesContentKey)

// We ignore the case when the editor has been cleared. If we don't have some content
// in local storage we used the summaries original content.
if (localStorageSavedContent !== null && localStorageSavedContent !== ""){
 editor.setValue(localStorageSavedContent, 1)
}

// Perform initial render
onContentsUpdated(editor.getValue())
