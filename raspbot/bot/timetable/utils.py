from aiogram import types
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import messages as msg
from raspbot.bot.constants import states
from raspbot.bot.timetable import keyboards as kb
from raspbot.core.logging import configure_logging
from raspbot.db.routes.schema import ThreadResponse
from raspbot.services.timetable import Timetable

logger = configure_logging(name=__name__)


# TODO: the two functions below can be merged
async def process_today_timetable_callback(
    callback: types.CallbackQuery,
    state: FSMContext,
    timetable_obj: Timetable,
):
    """Answers the callback based on the provided Timetable object for today."""
    timetable_obj_msgs: tuple = await timetable_obj.msg
    for part in timetable_obj_msgs:
        await callback.message.answer(
            text=part,
            reply_markup=await kb.get_today_departures_keyboard(
                timetable_obj=timetable_obj
            ),
            parse_mode="HTML",
        )
    await callback.answer()
    await state.update_data(timetable_obj=timetable_obj)
    await state.set_state(states.TimetableState.exact_departure_info)


async def process_date_timetable_callback(
    callback: types.CallbackQuery,
    state: FSMContext,
    timetable_obj: Timetable,
):
    """Answers the callback based on the provided Timetable object for certain date."""
    timetable_obj_msgs = await timetable_obj.msg
    for part in timetable_obj_msgs:
        await callback.message.answer(
            text=part,
            reply_markup=await kb.get_date_departures_keyboard(
                route_id=timetable_obj.route.id
            ),
            parse_mode="HTML",
        )
    await callback.answer()
    await state.update_data(timetable_obj=timetable_obj)
    await state.set_state(states.TimetableState.exact_departure_info)


async def get_timetable_object_from_state(state: FSMContext) -> Timetable | None:
    """Get the timetable object from the FSM Context state dictionary.

    Args:
        state: current FSMContext

    Returns:
        Timetable object or None

    """
    user_data: dict = await state.get_data()
    try:
        timetable_obj: Timetable = user_data["timetable_obj"]
    except TypeError as e:
        logger.error(f"user_data is not a dict: {e}")
        return None
    except KeyError:
        logger.error("There is no 'timetable_obj' key in the user_data dict.")
        return None
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
        dep_info: ThreadResponse = next(dep for dep in timetable if dep.uid == uid)
    except StopIteration:
        # TODO: Complete error handling
        logger.error("StopIteration error")
    msg_obj = msg.ThreadInfo(thread=dep_info)
    if full_kb:
        reply_markup = await kb.get_separate_departure_keyboard(
            this_departure=dep_info,
            timetable_obj=timetable_obj,
        )
    else:
        reply_markup = kb.get_date_departures_keyboard(route_id=timetable_obj.route.id)
    await message.answer(
        text=str(msg_obj),
        reply_markup=reply_markup,
        parse_mode="HTML",
    )
