from shapely import set_srid, to_wkb, wkt


def ewkb_from_wkt(
    value: str,
    *,
    srid: int = 2056,
) -> bytes:
    geometry = wkt.loads(
        value,
    )

    geometry = set_srid(
        geometry,
        srid,
    )

    return to_wkb(
        geometry,
        hex=False,
        include_srid=True,
    )
