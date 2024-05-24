from aiogram import types
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import messages as msg
from raspbot.bot.routes.keyboards import (
    get_point_choice_keyboard,
    get_single_point_confirmation_keyboard,
)
from raspbot.bot.start.keyboards import back_to_start_keyboard
from raspbot.core import exceptions as exc
from raspbot.core.email import send_email_async
from raspbot.core.logging import configure_logging, log
from raspbot.db.routes.schema import PointResponsePD
from raspbot.services.routes import PointSelector

logger = configure_logging(__name__)


@log(logger)
async def select_point(is_departure: bool, message: types.Message, state: FSMContext):
    """Base function for the departure / destination point selection."""
    point_selector = PointSelector()

    try:
        point_chunks: list[list[PointResponsePD]] | None = (
            await point_selector.select_points(raw_user_input=message.text)
        )
    except exc.UserInputTooShortError as e:
        logger.error(e, exc_info=True)
        await message.answer(
            text=msg.INPUT_TOO_SHORT, reply_markup=back_to_start_keyboard()
        )
    except Exception as e:
        logger.exception(e)
        await message.answer(text=msg.ERROR, reply_markup=back_to_start_keyboard())
        await send_email_async(e)

    if not point_chunks:
        await message.answer(
            text=msg.POINT_NOT_FOUND, reply_markup=back_to_start_keyboard()
        )
    elif len(point_chunks) > 1 or len(point_chunks[0]) > 1:
        logger.debug(f"Number of point chunks before pop: {len(point_chunks)}.")
        points: list = point_chunks.pop(0)
        logger.debug(f"First point chunk popped, its length is {len(points)} elements.")
        logger.debug(f"Number of point chunks after pop is {len(point_chunks)} chunks.")
        logger.debug(
            f"Bool value of last chunk given to keyboard is {not point_chunks}."
        )
        await message.answer(
            msg.MULTIPLE_POINTS_FOUND,
            reply_markup=get_point_choice_keyboard(
                points=points, is_departure=is_departure, last_chunk=not point_chunks
            ),
        )
        logger.debug("Updating the state user data with remanining point chunks.")
        await state.update_data(remaining_point_chunks=point_chunks)
        user_data: dict = await state.get_data()
        logger.debug(
            "Amount of remaining chunks in the state user data is "
            f"{len(user_data['remaining_point_chunks'])} chunks."
        )
    else:
        point = point_chunks[0][0]
        msg_text = msg.SinglePointFound(point=point, is_departure=is_departure)
        await message.answer(
            text=f"{msg_text} {msg.WHAT_YOU_WERE_LOOKING_FOR}",
            reply_markup=get_single_point_confirmation_keyboard(
                point=point, is_departure=is_departure
            ),
        )
