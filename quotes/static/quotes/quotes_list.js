/* globals axios */

document.addEventListener('DOMContentLoaded', function(){
    // Register click listeners to all vote up and vote down buttons we can find.
    // The quote ids are stored as data attributes on the button elements themselves.
    var voteUps = document.querySelectorAll(".quote__voteup");
    voteUps.forEach(function(element){
        var quoteId = element.getAttribute('data-quote-id');
        element.addEventListener('click', function(){
            axios('/internal/quotes/' + quoteId + '/vote-up', {method: 'POST'})
                .then(function(response){
                    // `element` is the vote up button, and its sibling with class .quote__sum contains
                    // the actual quote sum data.
                    element.parentNode.querySelector('.quote__sum').innerHTML = "Score: " + response.data.sum;
                })

        });
    });
    var approveQuote = document.querySelectorAll(".quote__approve");
    approveQuote.forEach(function(element){
        var quoteId = element.getAttribute('data-quote-id');
        element.addEventListener('click', function(){
            axios('/internal/quotes/' + quoteId + '/approve', {method: 'POST'})
                .then(function(response){
                    // `element` is the vote down button, and its sibling with class .quote__sum contains
                    // the actual quote sum data.
                    location.reload();
                })
        });
    });
    var voteDowns = document.querySelectorAll(".quote__votedown");
    voteDowns.forEach(function(element){
        var quoteId = element.getAttribute('data-quote-id');
        element.addEventListener('click', function(){
            axios('/internal/quotes/' + quoteId + '/vote-down', {method: 'POST'})
                .then(function(response){
                    // `element` is the vote down button, and its sibling with class .quote__sum contains
                    // the actual quote sum data.
                    element.parentNode.querySelector('.quote__sum').innerHTML = "Score: " + response.data.sum;
                })
        });
    });

});
