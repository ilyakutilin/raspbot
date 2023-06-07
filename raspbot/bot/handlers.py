from datetime import datetime

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from raspbot.apicalls.search import search_between_stations
from raspbot.bot.constants import callback as clb
from raspbot.bot.constants.states import Route
from raspbot.bot.constants.text import SinglePointFound, msg
from raspbot.bot.keyboards import PointChoiceKeyboard
from raspbot.core.logging import configure_logging
from raspbot.db.stations.schema import PointResponse
from raspbot.services.routes import point_retriever, point_selector

logger = configure_logging(name=__name__)

router = Router()


@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    """User: issues /start command. Bot: please input the departure point."""
    await message.answer(msg.INPUT_DEPARTURE_POINT)
    await state.set_state(Route.selecting_departure_point)


def _single_point_found_message_text(
    point: PointResponse,
    is_departure: bool,
) -> str:
    single_point_found = SinglePointFound(
        is_departure=is_departure,
        is_station=point.is_station,
        title=point.title,
        region_title=point.region_title,
    )
    return str(single_point_found)


async def select_point(is_departure: bool, message: types.Message, state: FSMContext):
    """Base function for the departure / destination point selection."""
    points: list[PointResponse] = await point_selector.select_points(
        raw_user_input=message.text
    )
    if not points:
        await message.answer(text=msg.POINT_NOT_FOUND)
    elif len(points) > 1:
        kb = PointChoiceKeyboard(points=points, is_departure=is_departure)
        await message.answer(
            msg.MULTIPLE_POINTS_FOUND, reply_markup=kb.get_exact_keyboard()
        )
        await state.update_data(full_point_list=points)
    else:
        msg_text: str = _single_point_found_message_text(
            point=points[0], is_departure=is_departure
        )
        if is_departure:
            await message.answer(text=f"{msg_text}\n\n{msg.INPUT_DESTINATION_POINT}")
            await state.update_data(departure_point=points[0])
            await state.set_state(Route.selecting_destination_point)
        else:
            await state.update_data(destination_point=points[0])
            timetable: list[str] = await search_timetable(state=state)
            await message.answer(text=f"{msg_text}\n\n{', '.join(timetable)}")
            await state.clear()


@router.message(Route.selecting_departure_point)
async def select_departure(message: types.Message, state: FSMContext):
    """User: inputs the desired departure point. Bot: here's what I have in the DB."""
    await select_point(is_departure=True, message=message, state=state)


@router.message(Route.selecting_destination_point)
async def select_destination(message: types.Message, state: FSMContext):
    """User: inputs the destination point. Bot: here's what I have in the DB."""
    await select_point(is_departure=False, message=message, state=state)


@router.callback_query(clb.MissingPointCallbackFactory.filter(F.exact == True))  # noqa
async def missing_exact_point_callback(
    callback: types.CallbackQuery,
    callback_data: clb.MissingPointCallbackFactory,
    state: FSMContext,
):
    """User: clicks the 'missing' button when exact. Bot: let's try non-exact."""
    is_departure = callback_data.is_departure
    user_data: dict = await state.get_data()
    full_point_list: list[PointResponse] = user_data["full_point_list"]
    kb = PointChoiceKeyboard(points=full_point_list, is_departure=is_departure)
    await callback.message.answer(
        msg.MISSING_POINT_EXACT, reply_markup=kb.get_inexact_keyboard()
    )
    await callback.answer()


@router.callback_query(clb.MissingPointCallbackFactory.filter(F.exact == False))  # noqa
async def missing_nonexact_point_callback(
    callback: types.CallbackQuery,
    callback_data: clb.MissingPointCallbackFactory,
    state: FSMContext,
):
    """User: clicks the 'missing' button when non-exact. Bot: please start again."""
    is_departure = callback_data.is_departure
    await callback.message.answer(
        msg.INPUT_DEPARTURE_POINT if is_departure else msg.INPUT_DESTINATION_POINT
    )
    await callback.answer()
    await state.set_state(
        Route.selecting_departure_point
        if is_departure
        else Route.selecting_destination_point
    )


@router.callback_query(clb.PointsCallbackFactory.filter(F.is_departure == True))  # noqa
async def choose_departure_from_multiple_callback(
    callback: types.CallbackQuery,
    callback_data: clb.PointsCallbackFactory,
    state: FSMContext,
):
    """User: selects the departure from the list. Bot: input the destination point."""
    selected_departure: PointResponse = await point_retriever.get_point(
        point_id=callback_data.point_id, is_station=callback_data.is_station
    )
    msg_text: str = _single_point_found_message_text(
        point=selected_departure, is_departure=callback_data.is_departure
    )
    await callback.message.answer(text=f"{msg_text}\n{msg.INPUT_DESTINATION_POINT}")
    await callback.answer()
    await state.update_data(departure_point=selected_departure)
    await state.set_state(Route.selecting_destination_point)


@router.callback_query(
    clb.PointsCallbackFactory.filter(F.is_departure == False)  # noqa
)
async def choose_destination_from_multiple_callback(
    callback: types.CallbackQuery,
    callback_data: clb.PointsCallbackFactory,
    state: FSMContext,
):
    """User: selects the destination from the list. Bot: here's the timetable."""
    selected_point: PointResponse = await point_retriever.get_point(
        point_id=callback_data.point_id, is_station=callback_data.is_station
    )
    msg_text: str = _single_point_found_message_text(
        point=selected_point, is_departure=callback_data.is_departure
    )
    await state.update_data(destination_point=selected_point)
    timetable: list[str] = await search_timetable(state=state)
    await callback.message.answer(text=f"{msg_text}\n{', '.join(timetable)}")
    await callback.answer()
    await state.clear()


async def search_timetable(state: FSMContext):
    user_data: dict = await state.get_data()
    logger.info(f"User data: {user_data}")
    departure_point: PointResponse | None = user_data.get("departure_point")
    destination_point: PointResponse | None = user_data.get("destination_point")
    timetable_dict: dict = await search_between_stations(
        from_=departure_point.yandex_code,
        to=destination_point.yandex_code,
        date=str(datetime.today()).split()[0],
    )
    logger.info(f"Кол-во рейсов от Яндекса: {len(timetable_dict['segments'])}")
    closest_departures: list[datetime] = []
    for segment in timetable_dict["segments"]:
        departure: str = segment["departure"]
        try:
            departure_time: datetime = datetime.fromisoformat(departure)
        except ValueError as e:
            logger.error(e)
            try:
                departure_time: datetime = datetime.strptime(departure, "%H:%M:%S")
            except ValueError as e:
                logger.error(e)
                print(
                    "Время пришло от Яндекса в некорректном формате. Поддерживаются "
                    f"2023-05-29T12:48:00.000000 или 12:48:00, а пришло {departure}."
                )
        if (
            departure_time < datetime.now(tz=departure_time.tzinfo)
            or len(closest_departures) > 10
        ):
            logger.info(
                "Отбраковка: Текущее время: "
                f"{datetime.now(tz=departure_time.tzinfo)},"
                f"Кол-во рейсов в списке: {len(closest_departures)},"
                "Время отправления от Яндекса: "
                f"{departure_time.strftime('%H:%M')}"
            )
            continue
        closest_departures.append(departure_time)
    logger.info(f"Финальное кол-во рейсов в списке: {len(closest_departures)}")
    timetable: list[str] = []
    for dep in closest_departures:
        timetable.append(dep.strftime("%H:%M"))
    return timetable
