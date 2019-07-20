/* global ace, createDelay, showdown, copyContentsToClipboard */

// Find current summary id.
const summaryId = document.querySelector('meta[name="summary-update-id"]').getAttribute("content")
// Find current summary version
const summaryVersion = document.querySelector('meta[name="summary-update-version"]').getAttribute("content")
// Find original contents, in case we want to discard the draft
const summaryContents = document.querySelector('meta[name="summary-update-original-contents"]').getAttribute("content")

// This variable is used to save temporary edits to the local storage.
const localStorageSummariesContentKey = 'summaries-update-contents-' + summaryId
const localStorageSummariesVersionKey = 'summaries-update-contents-' + summaryId + '-version'

// Get references to some of the essential elements
const previewEl = document.getElementById("summaryupdate-preview")
const contentsInputEl = document.getElementById("summaryupdate-contentsinput")
const submitEl = document.getElementById("summaryupdate-submit")
const formEl = document.getElementById("summaryupdate-form")

// We use the delay-wrapper to delay updating our preview until a batch of inputs
// have finished (we use 500 ms to separate the batches)
const delayWrapper = createDelay()
const delayPeriod = 500  // ms

// Set up editor
const editor = ace.edit("summaryupdate-contents", {
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
    localStorage.removeItem(localStorageSummariesVersionKey)

    formEl.submit()
})

// If we have some saved content in localStorage, add it.
const localStorageSavedContent = localStorage.getItem(localStorageSummariesContentKey)
const localStorageSavedVersion = localStorage.getItem(localStorageSummariesVersionKey)

// We ignore the case when the editor has been cleared. If we don't have some content
// in local storage we used the summaries original content.
if (localStorageSavedContent !== null && localStorageSavedContent !== ""){
    // If the remote version has changed since the last time, we always use the new version
    // This clause checks for the opposite; whether or not the version has not changed (or we haven't cached a verrsion)
    if (localStorageSavedVersion === summaryVersion){
        editor.setValue(localStorageSavedContent, 1)
    } else if (localStorageSavedVersion !== null) {
        // TODO: Alert the user about the fact that his/her content has been overwritten, and save
        // the contents to the clipboard.
    }
}

// Save current version
localStorage.setItem(localStorageSummariesVersionKey, summaryVersion)

// Perform initial render
onContentsUpdated(editor.getValue())
