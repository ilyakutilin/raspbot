import datetime as dt
import smtplib
import traceback
import types
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging, log
from raspbot.settings import settings as s

logger = configure_logging(__name__)


def _get_exception_details(
    exception: Exception,
) -> tuple[str, types.TracebackType, str, str]:
    """Get the exception details."""
    exc_name = exception.__class__.__name__
    tb = exception.__traceback__
    # Iterate through the traceback object to get the last call in the stack
    while tb.tb_next:
        tb = tb.tb_next
    # Get the frame object
    frame = tb.tb_frame
    # Get the function name and the module name where the exception occurred
    function_name = frame.f_code.co_name
    module_name = frame.f_globals["__name__"]
    # Get the formatted tracebck to be included in the email
    tb_str = "\n".join(traceback.format_tb(exception.__traceback__))

    return exc_name, tb_str, function_name, module_name


@log(logger)
def _create_email_message_from_text(
    text: str,
    from_email: str = s.EMAIL_FROM,
    to_email: str = s.EMAIL_TO,
    content_type: str = "plain",
    charset: str = "utf-8",
) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email

    msg["Subject"] = "Internal message from Raspbot"

    message = text
    msg.attach(MIMEText(message, content_type, charset))

    return msg


@log(logger)
def _create_email_message_from_exception(
    exception: Exception,
    from_email: str = s.EMAIL_FROM,
    to_email: str = s.EMAIL_TO,
    content_type: str = "plain",
    charset: str = "utf-8",
) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email

    exc_name, tb_str, func_name, module_name = _get_exception_details(exception)

    msg["Subject"] = f"{exc_name} occurred in {module_name} / {func_name}."

    message = (
        f"{exception.__class__.__name__} {exception} occurred "
        f"in module {module_name} / function {func_name} "
        f"on {dt.datetime.now().strftime('%d.%m.%Y at %H:%M:%S.%f')}.\n\n"
        f"Traceback: {tb_str}"
    )
    msg.attach(MIMEText(message, content_type, charset))

    return msg


@log(logger)
def _get_smtp_params() -> tuple[str, str, str, int]:
    """Get SMTP parameters from settings."""
    host = s.EMAIL_HOST
    user = s.EMAIL_USER
    password = s.EMAIL_PASSWORD
    port = s.EMAIL_PORT
    return host, user, password, port


@log(logger)
def send_email(payload: str | Exception):
    """Send an email with error info to bot admin."""
    host, user, password, port = _get_smtp_params()

    if isinstance(payload, Exception):
        msg = _create_email_message_from_exception(payload)
    elif isinstance(payload, str):
        msg = _create_email_message_from_text(payload)
    else:
        raise exc.EmailSendingAttributesError(
            "You must provide either a text or an exception object."
        )

    try:
        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
        logger.debug("Email sent to admin.")
    except Exception as e:
        logger.error(f"Failed to send email to admin: {e}")
    finally:
        server.quit()


@log(logger)
async def send_email_async(payload: str | Exception):
    """Send an email with error info to bot admin from within an async function."""
    host, user, password, port = _get_smtp_params()

    if isinstance(payload, Exception):
        msg = _create_email_message_from_exception(payload)
    elif isinstance(payload, str):
        msg = _create_email_message_from_text(payload)
    else:
        raise exc.EmailSendingAttributesError(
            "You must provide either a text or an exception object."
        )

    try:
        await aiosmtplib.send(
            msg,
            hostname=host,
            port=port,
            username=user,
            password=password,
            start_tls=True,
        )
        logger.debug("Email sent to admin.")
    except Exception as e:
        logger.error(f"Failed to send email to admin: {e}")
