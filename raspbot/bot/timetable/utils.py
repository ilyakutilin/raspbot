import datetime as dt
import inspect

from aiogram import types
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import messages as msg
from raspbot.bot.constants import states
from raspbot.bot.start.keyboards import back_to_start_keyboard
from raspbot.bot.timetable import keyboards as kb
from raspbot.core import exceptions as exc
from raspbot.core.email import send_email_async
from raspbot.core.logging import configure_logging
from raspbot.db.models import RouteORM, UserORM
from raspbot.db.routes.schema import RouteResponsePD, ThreadResponsePD
from raspbot.services.timetable import ThreadInfo, Timetable
from raspbot.services.users import get_recent_by_route, get_user_from_db_or_raise

logger = configure_logging(name=__name__)


async def _route_is_in_user_fav(
    route: RouteORM | RouteResponsePD, user: UserORM
) -> bool:
    """Check if the route is in the user's favorite routes."""
    try:
        recent = await get_recent_by_route(user_id=user.id, route_id=route.id)
    except exc.NotFoundError:
        return False
    if recent.favorite:
        return True
    return False


async def _answer_with_timetable(
    timetable_obj: Timetable, message: types.Message, user: UserORM
) -> None:
    """Answers the message with the provided Timetable object."""
    try:
        timetable_obj_msgs: tuple[str] = await timetable_obj.msg
    except exc.APIError:
        await message.answer(
            text=msg.API_CONNECTION_ERROR, reply_markup=back_to_start_keyboard()
        )
    except Exception:
        await message.answer(text=msg.ERROR, reply_markup=back_to_start_keyboard())

    route_is_in_user_fav = await _route_is_in_user_fav(
        route=timetable_obj.route, user=user
    )

    if timetable_obj.date == dt.date.today():
        reply_markup = await kb.get_today_departures_keyboard(
            timetable_obj=timetable_obj, route_is_in_user_fav=route_is_in_user_fav
        )
    else:
        reply_markup = await kb.get_date_departures_keyboard(
            route_id=timetable_obj.route.id,
            route_is_in_user_fav=route_is_in_user_fav,
        )
    for i, part in enumerate(timetable_obj_msgs):
        if i == len(timetable_obj_msgs) - 1:
            await message.answer(
                text=part,
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        else:
            await message.answer(
                text=part,
                reply_markup=None,
                parse_mode="HTML",
            )


async def process_timetable_callback(
    callback: types.CallbackQuery,
    state: FSMContext,
    timetable_obj: Timetable,
):
    """Answers the callback based on the provided Timetable object."""
    try:
        user = await get_user_from_db_or_raise(callback.from_user.id)
    except Exception as e:
        logger.exception(e)
        await send_email_async(e)
        assert isinstance(callback.message, types.Message)
        await callback.message.answer(
            text=msg.ERROR, reply_markup=back_to_start_keyboard()
        )

    assert isinstance(callback.message, types.Message)

    await _answer_with_timetable(timetable_obj, callback.message, user)
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
    try:
        assert message.from_user
        user = await get_user_from_db_or_raise(message.from_user.id)
    except Exception as e:
        logger.exception(e)
        await send_email_async(e)
        await message.answer(text=msg.ERROR, reply_markup=back_to_start_keyboard())

    await _answer_with_timetable(timetable_obj, message, user)
    await state.set_state(states.TimetableState.exact_departure_info)
    await state.update_data(timetable_obj=timetable_obj)


async def get_timetable_object_from_state(state: FSMContext) -> Timetable:
    """Get the timetable object from the FSM Context state dictionary."""
    user_data: dict = await state.get_data()
    try:
        return user_data["timetable_obj"]
    except TypeError as e:
        logger.error(f"user_data is not a dict: {e}")
        raise exc.UserDataNotADictError
    except KeyError:
        logger.error("There is no 'timetable_obj' key in the user_data dict.")
        raise exc.NoKeyError


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
        frame = inspect.currentframe()
        assert frame and frame.f_back
        error_msg = (
            f"UID {uid} provided by the callback "
            f"{frame.f_back.f_code.co_name} and passed to "
            f"{frame.f_code.co_name} is not found in the timetable "
            f"{timetable_obj}."
        )
        logger.error(error_msg)
        raise exc.NoUIDInTimetableError(error_msg)

    msg_obj = ThreadInfo(thread=dep_info)
    msg_text = await msg_obj.msg
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
        text=msg_text,
        reply_markup=reply_markup,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
