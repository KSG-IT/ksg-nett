from rest_framework.exceptions import APIException


class InsufficientFundsException(APIException):
    status_code = 402
    status_detail = "This Soci bank account has insufficient funds."


class NoSociSessionError(APIException):
    status_code = 424
    status_detail = "Since there is currently no active Soci session, this operation cannot be performed."
