from datetime import datetime, timezone


def get_current_time_as_iso_str() -> str:
    now = datetime.now(timezone.utc)
    iso_format = now.isoformat()
    iso_json_format = iso_format.replace("+00:00", "Z")

    return iso_json_format
