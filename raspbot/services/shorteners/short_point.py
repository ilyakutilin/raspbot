from raspbot.core.logging import configure_logging, log
from raspbot.db.models import PointTypeEnum

logger = configure_logging(__name__)


@log(logger)
def get_short_point_type(point_type: PointTypeEnum) -> str:
    """
    Generates abbreviation for the type of departure or destination - "ст." or "г.".

    Accepts:
        point_type (PointTypeEnum): Point type in Enum format.

    Returns:
        str: "ст." for station or "г." for settlement.
    """
    if point_type == PointTypeEnum.station:
        return "ст."
    return "г."
