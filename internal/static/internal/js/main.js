/* globals axios */
// noinspection JSUnusedGlobalSymbols

/**
 * Expose a global method for finding the current csrf token.
 */
window.getCsrfToken = function(){
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content')
}

document.addEventListener('DOMContentLoaded', function(){
    // Set up axios with proper defaults
    axios.defaults.headers.common['X-CSRFTOKEN'] = getCsrfToken();
});

/**
 * createDelay is a helper function allowing us to
 * cause a delay before a callback is called. If
 * the returned function is called more than once, the previous
 * timeout is cleared, and a new one is created.
 * Example usage:
 *   <pre>
 *   <code>
 *      const delayWrapper = DelayUntil()
 *      // Will only log a click that is not succeeded by another click for
 *      // at least one second.
 *      element.addEventHandler('click', delayWrapper(console.log, 1000)))
 *   </code>
 *   </pre>
 *   ```
 */
window.createDelay = function(){
    let timer = 0;
    return function(callback, ms, args){
        clearTimeout(timer)
        timer = setTimeout(callback.bind(null, args), ms)
    }
}

/**
 * copyContentsToClipboard is a helper function which copies some contents
 * to the users clipboard.
 *
 * The method used is the 'standard' one, in which a textarea element is created,
 * positioned somewhere off-screen, and given the contents as value. The textarea
 * is then programatically selected, and the command 'copy' is executed on the
 * main document instance.
 */
window.copyContentsToClipboard = function(contents){
    const hiddenTextAreaEl = document.createElement('input');
    hiddenTextAreaEl.value = contents;
    hiddenTextAreaEl.setAttribute('readonly', '');
    // Hide the element off-screen
    hiddenTextAreaEl.style.position = 'absolute';
    hiddenTextAreaEl.style.left = '0';
    hiddenTextAreaEl.style.top = '0';

    // Add to document, to make it selectable
    document.body.appendChild(hiddenTextAreaEl);

    // Select and copy
    hiddenTextAreaEl.select();
    const result = document.execCommand('copy');
    console.log(result)

    // Clean up
    // document.body.removeChild(hiddenTextAreaEl);
}
