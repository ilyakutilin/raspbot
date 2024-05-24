import datetime as dt

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from raspbot.bot.constants import callback as clb
from raspbot.bot.constants import messages as msg
from raspbot.bot.constants import states
from raspbot.bot.start.keyboards import back_to_start_keyboard
from raspbot.bot.timetable import utils
from raspbot.core import exceptions as exc
from raspbot.core.email import send_email_async
from raspbot.core.logging import configure_logging
from raspbot.db.models import RecentORM, RouteORM
from raspbot.services.deptime import get_uid_by_time
from raspbot.services.other_date import get_timetable_by_date
from raspbot.services.routes import RouteRetriever
from raspbot.services.timetable import Timetable
from raspbot.services.users import update_recent
from raspbot.settings import settings

logger = configure_logging(name=__name__)

router = Router()

route_retriever = RouteRetriever()


@router.callback_query(clb.GetTimetableCallbackFactory.filter())
async def show_closest_departures_callback(
    callback: types.CallbackQuery,
    callback_data: clb.GetTimetableCallbackFactory,
    state: FSMContext,
):
    """User: selects the route from the list. Bot: here's the timetable.

    Current state: TimetableState:exact_departure_info
    """
    try:
        recent: RecentORM = await update_recent(recent_id=callback_data.recent_id)
        route: RouteORM = await route_retriever.get_route_from_db(
            route_id=recent.route_id
        )
    # Exception includes the most common NoDBObjectError exception
    except Exception as e:
        logger.exception(e)
        assert isinstance(callback.message, types.Message)
        await callback.message.answer(
            text=msg.ERROR, reply_markup=back_to_start_keyboard()
        )
        await send_email_async(e)

    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} "
        f"selected route {route} from an inline keyboard."
    )
    timetable_obj = Timetable(route=route, limit=settings.CLOSEST_DEP_LIMIT)
    logger.info(
        f"Timetable_object for route {route} for today with threads limit of "
        f"{settings.CLOSEST_DEP_LIMIT} created: {timetable_obj}. "
        "Now replying to the user with this timetable."
    )
    await utils.process_timetable_callback(
        callback=callback, state=state, timetable_obj=timetable_obj
    )


@router.callback_query(clb.DepartureUIDCallbackFactory.filter())
async def show_departure_callback(
    callback: types.CallbackQuery,
    callback_data: clb.DepartureUIDCallbackFactory,
    state: FSMContext,
):
    """User: clicks on departure time. Bot: here's the departure info.

    Current state: TimetableState:exact_departure_info
    """
    assert isinstance(callback.message, types.Message)

    try:
        timetable_obj = await utils.get_timetable_object_from_state(state=state)
    except exc.InternalError:
        await callback.message.answer(
            text=msg.ERROR, reply_markup=back_to_start_keyboard()
        )
    uid: str = callback_data.uid

    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} "
        f"selected a departure from an inline keyboard. Replying with departure info."
    )

    try:
        await utils.show_dep_info(
            timetable_obj=timetable_obj, uid=uid, message=callback.message
        )
    except exc.NoUIDInTimetableError as e:
        await send_email_async(e)
        await callback.message.answer(
            text=msg.ERROR, reply_markup=back_to_start_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data == clb.SAME_DEPARTURE)
async def same_departure_callback(callback: types.CallbackQuery, state: FSMContext):
    """User: clicks on the same departure. Bot: here's an error message.

    Current state: TimetableState:exact_departure_info
    """
    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} "
        "clicked on the same departure. Replying with an error message."
    )
    await callback.answer(text=msg.SAME_DEPARTURE, show_alert=True)


@router.callback_query(clb.EndOfTheDayTimetableCallbackFactory.filter())
async def show_till_the_end_of_the_day_callback(
    callback: types.CallbackQuery,
    callback_data: clb.EndOfTheDayTimetableCallbackFactory,
    state: FSMContext,
):
    """User: clicks on the button to see full timetable for today. Bot: here you go.

    Current state: TimetableState:exact_departure_info
    """
    route_id: int = callback_data.route_id
    assert isinstance(callback.message, types.Message)

    try:
        timetable_obj: Timetable = await utils.get_timetable_object_from_state(
            state=state
        )
    except exc.InternalError as e:
        logger.exception(e)
        await callback.message.answer(
            text=msg.ERROR, reply_markup=back_to_start_keyboard()
        )
        await send_email_async(e)

    timetable_obj = timetable_obj.unlimit()
    if timetable_obj.route.id != route_id:
        try:
            route: RouteORM = await route_retriever.get_route_from_db(route_id=route_id)
        except Exception as e:
            logger.exception(e)
            await callback.message.answer(
                text=msg.ERROR, reply_markup=back_to_start_keyboard()
            )
            await send_email_async(e)
        timetable_obj = Timetable(route=route)

    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} "
        "clicked on an inline keyboard button to see the full timetable for "
        f"route {timetable_obj.route} for today. Replying with full timetable."
    )
    await utils.process_timetable_callback(
        callback=callback, state=state, timetable_obj=timetable_obj
    )


@router.message(states.TimetableState.exact_departure_info)
async def select_departure_info_by_text(message: types.Message, state: FSMContext):
    """User: types departure time. Bot: here's the departure info.

    Args:
        message: user input
        state: the current FSM state

    Current state: TimetableState:exact_departure_info
    """
    try:
        timetable_obj: Timetable = await utils.get_timetable_object_from_state(
            state=state
        )
    except exc.InternalError as e:
        logger.exception(e)
        await message.answer(text=msg.ERROR, reply_markup=back_to_start_keyboard())
        await send_email_async(e)

    timetable_obj = timetable_obj.unlimit()

    assert message.from_user
    logger.info(
        f"User {message.from_user.full_name} TGID {message.from_user.id} "
        f"entered the time '{message.text}'. Parsing user input and replying "
        "with the departure info."
    )
    try:
        uid: str = await get_uid_by_time(
            user_raw_time_input=message.text, timetable_obj=timetable_obj
        )
        logger.debug(f"uid is {uid}")
        try:
            await utils.show_dep_info(
                timetable_obj=timetable_obj, uid=uid, message=message, full_kb=False
            )
        except exc.NoUIDInTimetableError as e:
            await send_email_async(e)
            await message.answer(text=msg.ERROR, reply_markup=back_to_start_keyboard())
    except exc.InvalidDataError as e:
        await message.answer(text=str(e), reply_markup=back_to_start_keyboard())


@router.callback_query(clb.TomorrowTimetableCallbackFactory.filter())
async def show_tomorrow_timetable_callback(
    callback: types.CallbackQuery,
    callback_data: clb.TomorrowTimetableCallbackFactory,
    state: FSMContext,
):
    """User: clicks on the button to see timetable for tomorrow. Bot: here you go.

    Current state: TimetableState:exact_departure_info
    """
    route_id: int = callback_data.route_id

    try:
        route: RouteORM = await route_retriever.get_route_from_db(route_id=route_id)
    except Exception as e:
        logger.exception(e)
        assert isinstance(callback.message, types.Message)
        await callback.message.answer(
            text=msg.ERROR, reply_markup=back_to_start_keyboard()
        )
        await send_email_async(e)

    tomorrow = dt.date.today() + dt.timedelta(days=1)
    timetable_obj = Timetable(route=route, date=tomorrow)

    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} "
        "clicked on an inline keyboard button to see timetable for "
        f"route {timetable_obj.route} for tomorrow. Replying with the timetable."
    )
    await utils.process_timetable_callback(
        callback=callback, state=state, timetable_obj=timetable_obj
    )


@router.callback_query(clb.OtherDateTimetableCallbackFactory.filter())
async def show_other_date_timetable_callback(
    callback: types.CallbackQuery,
    callback_data: clb.OtherDateTimetableCallbackFactory,
    state: FSMContext,
):
    """User: clicks on button to see timetable for another date. Bot: enter the date.

    Current state: TimetableState:exact_departure_info
    """
    route_id: int = callback_data.route_id
    assert isinstance(callback.message, types.Message)

    try:
        route: RouteORM = await route_retriever.get_route_from_db(route_id=route_id)
    except Exception as e:
        logger.exception(e)
        await callback.message.answer(
            text=msg.ERROR, reply_markup=back_to_start_keyboard()
        )
        await send_email_async(e)

    logger.info(
        f"User {callback.from_user.full_name} TGID {callback.from_user.id} "
        f"clicked on an inline keyabord button to see the timetable for route {route} "
        "for an arbitrary date. Replying that they now need to input a date."
    )
    await callback.message.answer(
        text=msg.TYPE_ARBITRARY_DATE,
        reply_markup=back_to_start_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
    await state.set_state(states.TimetableState.other_date)
    await state.update_data(route=route)


@router.message(states.TimetableState.other_date)
async def select_date_timetable_by_text(message: types.Message, state: FSMContext):
    """User: types an arbitrary date. Bot: here's the timetable for this date.

    Current state: TimetableState:other_date
    """
    user_data: dict = await state.get_data()
    try:
        route = user_data["route"]
    except KeyError as e:
        logger.exception(f"There is no 'route' key in the state user data: {e}")
        await message.answer(text=msg.ERROR, reply_markup=back_to_start_keyboard())
        await send_email_async(e)

    assert message.from_user
    logger.info(
        f"User {message.from_user.full_name} TGID {message.from_user.id} "
        f"entered the date '{message.text}'. Parsing user input and replying "
        "with the timetable."
    )
    try:
        timetable_obj = get_timetable_by_date(
            route=route, user_raw_date_input=message.text
        )
        await utils.process_timetable_message(message, state, timetable_obj)
    except exc.InvalidDataError as e:
        await message.answer(
            text=str(e), reply_markup=back_to_start_keyboard(), parse_mode="HTML"
        )
    except exc.InternalError:
        await message.answer(text=msg.ERROR, reply_markup=back_to_start_keyboard())
