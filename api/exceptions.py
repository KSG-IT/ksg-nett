from rest_framework.exceptions import APIException


class InsufficientFundsException(APIException):
    status_code = 402
    status_detail = "This Soci bank account has insufficient funds."
