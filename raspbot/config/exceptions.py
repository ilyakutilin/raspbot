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
    "Base class for initial data related exceptions."


class DataStructureError(GetDataError):
    "Raised if there is an error in structuring the initial data."


# SQL


class SQLError(Exception):
    """Base class for SQL related exceptions."""


class SQLObjectError(SQLError):
    """Raised when there is an SQL object creation failure."""


class CreateSchemaError(SQLError):
    """Raised if there is an SQLAlchemy error."""
