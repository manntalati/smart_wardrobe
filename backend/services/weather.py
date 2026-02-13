"""
OpenWeatherMap integration for weather-aware outfit recommendations.
Uses the free tier (60 calls/min, 1M calls/month, no credit card required).
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather(city: str) -> dict | None:
    """
    Fetch current weather for a city.
    Returns a structured weather dict or None if unavailable.
    """
    if not OPENWEATHER_API_KEY:
        return None

    try:
        response = requests.get(BASE_URL, params={
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "imperial",  # Fahrenheit
        }, timeout=5)

        if response.status_code != 200:
            print(f"Weather API error: {response.status_code} - {response.text}")
            return None

        data = response.json()

        temp_f = data["main"]["temp"]
        feels_like_f = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        description = data["weather"][0]["description"]
        main_weather = data["weather"][0]["main"]
        wind_speed = data.get("wind", {}).get("speed", 0)

        return {
            "city": data["name"],
            "temperature_f": round(temp_f),
            "feels_like_f": round(feels_like_f),
            "humidity": humidity,
            "description": description,
            "main": main_weather,
            "wind_speed": round(wind_speed, 1),
            "style_hints": _get_style_hints(temp_f, main_weather, wind_speed),
        }
    except Exception as e:
        print(f"Weather API exception: {e}")
        return None


def _get_style_hints(temp_f: float, main_weather: str, wind_speed: float) -> list[str]:
    """
    Convert weather conditions into actionable style hints.
    """
    hints = []

    # Temperature-based hints
    if temp_f >= 85:
        hints.append("Very hot — wear lightweight, breathable fabrics like linen or cotton")
        hints.append("Opt for light colors to reflect heat")
        hints.append("Shorts, tank tops, or summer dresses recommended")
    elif temp_f >= 70:
        hints.append("Warm weather — light layers, t-shirts, and casual wear")
        hints.append("No heavy jacket needed")
    elif temp_f >= 55:
        hints.append("Mild/cool — consider a light jacket or cardigan")
        hints.append("Layering is ideal for this temperature")
    elif temp_f >= 40:
        hints.append("Chilly — wear a warm jacket or coat")
        hints.append("Consider sweaters or hoodies for warmth")
    else:
        hints.append("Cold weather — heavy coat, scarf, and warm layers recommended")
        hints.append("Wool, fleece, or down jackets ideal")

    # Precipitation hints
    if main_weather in ("Rain", "Drizzle", "Thunderstorm"):
        hints.append("Rainy — waterproof jacket or umbrella recommended")
        hints.append("Avoid suede or delicate fabrics")
        hints.append("Waterproof boots or shoes advisable")
    elif main_weather == "Snow":
        hints.append("Snowy — insulated, waterproof boots and heavy coat essential")
        hints.append("Layered warm clothing recommended")

    # Wind hints
    if wind_speed > 15:
        hints.append("Windy — a windbreaker or structured jacket recommended")

    return hints
