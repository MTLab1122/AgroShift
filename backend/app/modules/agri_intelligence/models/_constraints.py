from .enums import GeographicScopeType


def geographic_scope_check(*, include_farm: bool) -> str:
    columns = [
        "country_id",
        "province_state_id",
        "district_id",
        "locality_id",
        "agroecological_zone_id",
    ]
    if include_farm:
        columns.append("farm_id")

    global_clause = " AND ".join(f"{column} IS NULL" for column in columns)
    clauses = [f"(scope_type = '{GeographicScopeType.GLOBAL.value}' AND {global_clause})"]
    scope_columns = {
        GeographicScopeType.COUNTRY.value: "country_id",
        GeographicScopeType.PROVINCE_STATE.value: "province_state_id",
        GeographicScopeType.DISTRICT.value: "district_id",
        GeographicScopeType.LOCALITY.value: "locality_id",
        GeographicScopeType.AGROECOLOGICAL_ZONE.value: "agroecological_zone_id",
    }
    if include_farm:
        scope_columns[GeographicScopeType.FARM.value] = "farm_id"

    for scope_type, selected_column in scope_columns.items():
        other_columns = [column for column in columns if column != selected_column]
        null_clause = " AND ".join(f"{column} IS NULL" for column in other_columns)
        clauses.append(
            f"(scope_type = '{scope_type}' AND {selected_column} IS NOT NULL "
            f"AND {null_clause})"
        )
    return " OR ".join(clauses)
