from common.util import send_email


def send_tagged_in_quote_email(quote, users):
    content = f"""
         Hei!

         Du har blitt tagget i et sitat

         Text: {quote.text}
         Context: {quote.context}

         """

    html_content = f"""
         <p>Hei!</p>
            <p>Du har blitt tagget i et sitat</p>
            <p>Text: {quote.text}</p>
            <p>Context: {quote.context}</p>

             """

    send_email(
        recipients=[user.email for user in users],
        subject="Du har blitt tagget i et sitat!",
        message=content,
        html_message=html_content,
    )
