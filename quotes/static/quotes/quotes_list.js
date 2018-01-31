
document.addEventListener('DOMContentLoaded', function(){

    // Register click listeners o all vote up and vote down buttons we can find.
    // The quote ids are stored as data attributes on the button elements themselves.
    var voteUps = document.querySelectorAll(".quote__voteup");
    voteUps.forEach(function(element){
        var quoteId = element.getAttribute('data-quote-id');
        element.addEventListener('click', function(){
            fetch('/internal/quotes/' + quoteId + '/vote-up', {method: 'POST'})
        });
    });
    var voteDowns = document.querySelectorAll(".quote__votedown");
    voteDowns.forEach(function(element){
        var quoteId = element.getAttribute('data-quote-id');
        element.addEventListener('click', function(){
            fetch('/internal/quotes/' + quoteId + '/vote-down', {method: 'POST'})
        });
    });
});
