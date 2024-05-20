import datetime as dt
import inspect

from aiogram import types
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import messages as msg
from raspbot.bot.constants import states
from raspbot.bot.timetable import keyboards as kb
from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging
from raspbot.db.routes.schema import ThreadResponsePD
from raspbot.services.timetable import Timetable

logger = configure_logging(name=__name__)


async def _answer_with_timetable(
    timetable_obj: Timetable, message: types.Message
) -> None:
    """Answers the message with the provided Timetable object."""
    try:
        timetable_obj_msgs: tuple[str] = await timetable_obj.msg
    except exc.APIError:
        await message.answer(msg.API_CONNECTION_ERROR)
    except Exception:
        await message.answer(msg.ERROR)

    if timetable_obj.date == dt.date.today():
        reply_markup = await kb.get_today_departures_keyboard(
            timetable_obj=timetable_obj
        )
    else:
        reply_markup = await kb.get_date_departures_keyboard(
            route_id=timetable_obj.route.id
        )
    for i, part in enumerate(timetable_obj_msgs):
        await message.answer(
            text=part,
            reply_markup=reply_markup if i == len(timetable_obj_msgs) - 1 else None,
            parse_mode="HTML",
        )


async def process_timetable_callback(
    callback: types.CallbackQuery,
    state: FSMContext,
    timetable_obj: Timetable,
):
    """Answers the callback based on the provided Timetable object."""
    await _answer_with_timetable(timetable_obj, callback.message)
    await callback.answer()

    logger.info(
        "Setting state to 'exact_departure_info' and updating the state data with "
        "the Timetable object."
    )
    await state.set_state(states.TimetableState.exact_departure_info)
    await state.update_data(timetable_obj=timetable_obj)


async def process_timetable_message(
    message: types.Message,
    state: FSMContext,
    timetable_obj: Timetable,
):
    """Answers the message based on the provided Timetable object."""
    await _answer_with_timetable(timetable_obj, message)
    await state.set_state(states.TimetableState.exact_departure_info)
    await state.update_data(timetable_obj=timetable_obj)


async def get_timetable_object_from_state(state: FSMContext) -> Timetable | None:
    """Get the timetable object from the FSM Context state dictionary."""
    user_data: dict = await state.get_data()
    try:
        timetable_obj: Timetable = user_data["timetable_obj"]
    except TypeError as e:
        logger.error(f"user_data is not a dict: {e}")
        raise exc.UserDataNotADictError
    except KeyError:
        logger.error("There is no 'timetable_obj' key in the user_data dict.")
        raise exc.NoKeyError
    return timetable_obj


async def show_dep_info(
    timetable_obj: Timetable, uid: str, message: types.Message, full_kb: bool = True
) -> None:
    """Answers the message with the departure info.

    :full_kb: if True, the keyboard that is added to the message contains buttons
              for the upcoming departures and 'Tomorrow' button. If False, the keyboard
              contains only one button for the other date.
    """
    timetable = await timetable_obj.timetable
    try:
        dep_info: ThreadResponsePD = next(dep for dep in timetable if dep.uid == uid)
    except StopIteration:
        error_msg = (
            f"UID {uid} provided by the callback "
            f"{inspect.currentframe().f_back.f_code.co_name} and passed to "
            f"{inspect.currentframe().f_code.co_name} is not found in the timetable "
            f"{timetable_obj}."
        )
        logger.error(error_msg)
        raise exc.NoUIDInTimetableError(error_msg)

    msg_obj = msg.ThreadInfo(thread=dep_info)
    if full_kb:
        reply_markup = await kb.get_separate_departure_keyboard(
            this_departure=dep_info,
            timetable_obj=timetable_obj,
        )
    else:
        reply_markup = await kb.get_date_departures_keyboard(
            route_id=timetable_obj.route.id
        )
    await message.answer(
        text=str(msg_obj),
        reply_markup=reply_markup,
        parse_mode="HTML",
    )
