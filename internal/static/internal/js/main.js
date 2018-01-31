// noinspection JSUnusedGlobalSymbols

/**
 * Expose a global method for finding the current csrf token.
 */
function getCsrfToken(){
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content')
}
