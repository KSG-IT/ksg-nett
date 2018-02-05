/* globals axios */
// noinspection JSUnusedGlobalSymbols

/**
 * Expose a global method for finding the current csrf token.
 */
function getCsrfToken(){
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content')
}

document.addEventListener('DOMContentLoaded', function(){
    // Set up axios with proper defaults
    axios.defaults.headers.common['X-CSRF-TOKEN'] = getCsrfToken();
});