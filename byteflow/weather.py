"""
Free, no-API-key current weather lookups via Open-Meteo
(https://open-meteo.com) - genuinely free for non-commercial use (up to
~10,000 requests/day), no signup, no key, no credit card. Uses only the
standard library (urllib, json), consistent with the rest of ByteFlow.

Why this exists: general web search (see web_search.py) is a poor way
to answer "what's the weather in X". DuckDuckGo's scraped HTML endpoint
is fragile and increasingly bot-blocked (see WebSearchError's
"anomaly page" handling), and even when it works, pulling a real
temperature out of a search snippet is unreliable. Weather is a
narrow, well-defined question with a purpose-built free API, so it's
answered directly through that API instead of being routed through
general search - faster, more accurate, and not subject to DDG's
bot-detection at all.
"""

import json
import urllib.request
import urllib.parse
import urllib.error


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_TIMEOUT = 10
_USER_AGENT = "ByteFlow/1.0 (+https://github.com/)"

# WMO weather interpretation codes, as used by Open-Meteo's
# `current_weather.weathercode` field - see https://open-meteo.com/en/docs
_WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow fall",
    73: "moderate snow fall",
    75: "heavy snow fall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


class WeatherError(Exception):
    pass


def _get_json(url, params):
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"
    request = urllib.request.Request(full_url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise WeatherError(f"Weather service request failed with HTTP {e.code}.") from e
    except urllib.error.URLError as e:
        raise WeatherError(f"Could not reach the weather service: {e.reason}.") from e
    except TimeoutError as e:
        raise WeatherError(f"Weather service request timed out. ({e})") from e

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise WeatherError(f"Weather service returned an unreadable response. ({e})") from e


def geocode(location):
    """
    Resolve a free-text place name to (lat, lon, display_name).
    Raises WeatherError if the location can't be resolved.
    """
    if not location or not location.strip():
        raise WeatherError("No location given.")

    data = _get_json(GEOCODE_URL, {"name": location.strip(), "count": 1})
    results = data.get("results") or []
    if not results:
        raise WeatherError(f"Could not find a location matching '{location}'.")

    top = results[0]
    name = top.get("name", location)
    admin1 = top.get("admin1")
    country = top.get("country")
    # de-dupe while preserving order (e.g. avoid "Ahmedabad, Ahmedabad")
    parts = list(dict.fromkeys(p for p in (name, admin1, country) if p))
    display_name = ", ".join(parts)

    return top["latitude"], top["longitude"], display_name


def get_current_weather(location):
    """
    Return a dict with current weather for `location`:
      {"location": "Ahmedabad, Gujarat, India", "temperature_c": 34.2,
       "windspeed_kmh": 11.3, "description": "clear sky",
       "is_day": True, "time": "2026-07-02T14:00"}

    Raises WeatherError on any failure (location not found, network
    issue, unexpected response shape) - callers should catch this and
    degrade gracefully, the same pattern as web_search.py's
    WebSearchError.
    """
    lat, lon, display_name = geocode(location)

    data = _get_json(FORECAST_URL, {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "timezone": "auto",
    })

    current = data.get("current_weather")
    if not current or "temperature" not in current:
        raise WeatherError(f"Weather service returned no current conditions for '{location}'.")

    code = current.get("weathercode")
    description = _WEATHER_CODES.get(code, "unknown conditions")

    return {
        "location": display_name,
        "temperature_c": current["temperature"],
        "windspeed_kmh": current.get("windspeed"),
        "description": description,
        "is_day": bool(current.get("is_day", 1)),
        "time": current.get("time"),
    }


def get_current_weather_formatted(location):
    """
    Convenience wrapper: get_current_weather() and format it as a
    single readable sentence, ready to show directly to a person or
    fold into an LLM prompt. Returns a clear message string (not an
    exception) if the lookup fails - safe to call directly from
    prompt-building or tool code.
    """
    try:
        w = get_current_weather(location)
    except WeatherError as e:
        return f"[Weather lookup unavailable: {e}]"

    temp_c = w["temperature_c"]
    temp_f = temp_c * 9 / 5 + 32
    wind = w["windspeed_kmh"]
    wind_part = f", wind {wind:.0f} km/h" if wind is not None else ""

    return (
        f"Current weather in {w['location']}: {w['description']}, "
        f"{temp_c:.1f}\u00b0C ({temp_f:.1f}\u00b0F){wind_part}."
    )
