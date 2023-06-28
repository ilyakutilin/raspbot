from raspbot.db.stations.models import PointTypeEnum


def get_short_point_type(point_type: PointTypeEnum) -> str:
    """
    Гененирует сокращение типа пункта отправления или назначения - ст. или г.

    Принимает на вход:
        point_type (PointTypeEnum): Тип пункта в формате Enum.

    Возвращает:
        str: Сокращение "ст." (станция) или "г." (город).
    """
    if point_type == PointTypeEnum.station:
        return "ст."
    return "г."
