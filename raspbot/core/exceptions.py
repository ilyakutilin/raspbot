# API and connectivity


class APIError(Exception):
    """Base class for the API and connection related exceptions."""


class EmptyHeadersError(APIError):
    """Raised if there is no Authorisation data in the headers."""


class APIStatusCodeError(APIError):
    """Raised if the endpoint is not available."""


class APIConnectionError(APIError):
    """Raised in case of general problems with the connection to API."""


# Initial Data


class GetDataError(Exception):
    """Base class for initial data related exceptions."""


class DataStructureError(GetDataError):
    """Raised if there is an error in structuring the initial data."""


# SQL


class SQLError(Exception):
    """Base class for SQL related exceptions."""


class SQLObjectError(SQLError):
    """Raised when there is an SQL object creation failure."""


class CreateSchemaError(SQLError):
    """Raised if there is an SQLAlchemy error."""


# Values


class InvalidDataError(ValueError):
    """Base class for all value-related exceptions."""


class InvalidValueError(InvalidDataError):
    """Raised if the value provided to a function is not valid."""


class UserInputTooShortError(InvalidDataError):
    """Raised if the user input is too short."""


class DateInThePastError(InvalidDataError):
    """Raised if the search date is set in the past."""


class InvalidTimeFormatError(InvalidDataError):
    """Raised if the time format received from Yandex cannot be processed."""


class InvalidTimeUserInputError(InvalidDataError):
    """Raised if user inputs the dep time in unreadable format."""


class InvalidDateUserInputError(InvalidDataError):
    """Raised if user inputs the date in unreadable format."""


class TimeNotFoundError(InvalidDataError):
    """Raised if the dep time cannot be found."""


# DB


class DBError(Exception):
    """Base class for DB related exceptions."""


class NotFoundError(DBError):
    """Raised if the object is not found."""


class AlreadyExistsError(DBError):
    """Raised if the object already exists."""


# Internal


class InternalError(Exception):
    """Base class for internal exceptions."""


class UserDataNotADictError(InternalError):
    """Raised if the user data is not a dict."""


class NoKeyError(InternalError):
    """Raised if the key is not in the dict."""
