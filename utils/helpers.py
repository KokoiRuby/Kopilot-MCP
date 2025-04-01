from datetime import datetime, timezone


__all__ = (
    "get_age_string",
    "get_ready_count",
    "to_plural",
)


def get_age_string(creation_timestamp):
    """Convert creation timestamp to human-readable age string"""
    if not creation_timestamp:
        return "Unknown"

    try:
        # Handle RFC3339 format (2023-01-01T12:00:00Z)
        if isinstance(creation_timestamp, str):
            # Try different timestamp formats
            formats_to_try = [
                "%Y-%m-%dT%H:%M:%SZ",  # Standard format
                "%Y-%m-%dT%H:%M:%S.%fZ",  # With microseconds
                "%Y-%m-%dT%H:%M:%S%z"  # With timezone
            ]

            for fmt in formats_to_try:
                try:
                    creation_time = datetime.strptime(
                        creation_timestamp, fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue
            else:  # If no format matched
                return "Unknown"
        else:
            # If it's already a datetime object
            creation_time = creation_timestamp

        now = datetime.now(timezone.utc)

        # Calculate the difference
        diff = now - creation_time

        # Format the age string
        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            return f"{days}d"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{minutes}m"
    except Exception as e:
        print(f"Error parsing timestamp: {e}")
        return "Unknown"


def get_ready_count(pod):
    """Get the ready container count as a string like '1/1'"""
    try:
        total = len(pod.spec.containers)
        ready = sum(
            1 for container in pod.status.containerStatuses if container.ready)
        return f"{ready}/{total}"
    except Exception:
        return "Unknown"


def to_plural(word: str) -> str:
    """Convert a word to its plural form"""
    if word.endswith('s') or word.endswith('x') or word.endswith('z') or word.endswith('ch') or word.endswith('sh'):
        return word + 'es'
    else:
        return word + 's'
