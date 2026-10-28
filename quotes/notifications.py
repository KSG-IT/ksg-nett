"""
The quote notifications, one function per event, with every channel. The
mutations call these through transaction.on_commit.
"""

from push.utils import PushMessage, send_to_users
from quotes.utils import send_tagged_in_quote_email


def notify_tagged_in_quote(quote, approver=None):
    """
    E-mail and push "you are quoted" to the users tagged in an approved quote.
    `notify_on_quote` decides the e-mail and `push_on_quote` the push. The
    approver gets no push.
    """
    emailed = quote.tagged.filter(notify_on_quote=True)
    if emailed:
        send_tagged_in_quote_email(quote, emailed)
    pushed = quote.tagged.filter(push_on_quote=True)
    if approver is not None:
        pushed = pushed.exclude(pk=approver.pk)
    recipient_ids = list(pushed.values_list("pk", flat=True))
    if not recipient_ids:
        return
    send_to_users(
        recipient_ids,
        PushMessage(
            title="Du er sitert",
            body=quote.text,
            path="/quotes",
            tag=f"quote-{quote.pk}",
        ),
    )
