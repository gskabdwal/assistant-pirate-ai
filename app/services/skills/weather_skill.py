"""
Weather forecast skill using OpenWeatherMap API for Captain Blackbeard's Voice Agent.
"""
import httpx
import logging
from typing import Dict, Any
from .base_skill import BaseSkill

logger = logging.getLogger(__name__)


class WeatherSkill(BaseSkill):
    """Weather forecast skill using OpenWeatherMap API."""
    
    def __init__(self, api_key: str):
        """
        Initialize weather skill.
        
        Args:
            api_key: OpenWeatherMap API key
        """
        super().__init__(
            name="weather",
            description="Get current weather and forecast for any location"
        )
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    def get_function_definition(self) -> Dict[str, Any]:
        """Get Gemini function calling definition for weather."""
        return {
            "name": "get_weather",
            "description": "Get current weather conditions and forecast for a specific location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, state/country (e.g., 'London', 'New York, NY', 'Paris, France')"
                    },
                    "forecast_days": {
                        "type": "integer",
                        "description": "Number of forecast days to include (1-5, default: 1)"
                    }
                },
                "required": ["location"]
            }
        }
    
    async def execute(self, location: str, forecast_days: int = 1) -> str:
        """
        Execute weather lookup.
        
        Args:
            location: Location to get weather for
            forecast_days: Number of forecast days
            
        Returns:
            Formatted weather information
        """
        try:
            logger.info(f"🌤️ Getting weather for: {location}")
            
            async with httpx.AsyncClient() as client:
                # Get current weather
                current_response = await client.get(
                    f"{self.base_url}/weather",
                    params={
                        "q": location,
                        "appid": self.api_key,
                        "units": "metric"
                    },
                    timeout=10.0
                )
                
                if current_response.status_code != 200:
                    logger.error(f"Weather API error: {current_response.status_code}")
                    return f"Arrr! The weather winds be unreadable for '{location}', matey!"
                
                current_data = current_response.json()
                
                # Format current weather
                results = []
                city_name = current_data.get("name", location)
                country = current_data.get("sys", {}).get("country", "")
                
                results.append(f"**Weather Report for {city_name}{', ' + country if country else ''}:**")
                
                # Current conditions
                main = current_data.get("main", {})
                weather = current_data.get("weather", [{}])[0]
                wind = current_data.get("wind", {})
                
                temp = main.get("temp", 0)
                feels_like = main.get("feels_like", 0)
                humidity = main.get("humidity", 0)
                description = weather.get("description", "").title()
                wind_speed = wind.get("speed", 0)
                
                results.append(f"🌡️ **Temperature:** {temp:.1f}°C (feels like {feels_like:.1f}°C)")
                results.append(f"☁️ **Conditions:** {description}")
                results.append(f"💧 **Humidity:** {humidity}%")
                results.append(f"💨 **Wind Speed:** {wind_speed} m/s")
                
                # Get forecast if requested
                if forecast_days > 1:
                    forecast_response = await client.get(
                        f"{self.base_url}/forecast",
                        params={
                            "q": location,
                            "appid": self.api_key,
                            "units": "metric",
                            "cnt": forecast_days * 8  # 8 forecasts per day (3-hour intervals)
                        },
                        timeout=10.0
                    )
                    
                    if forecast_response.status_code == 200:
                        forecast_data = forecast_response.json()
                        results.append("\n**Forecast:**")
                        
                        # Group by day and take midday forecast
                        daily_forecasts = {}
                        for item in forecast_data.get("list", []):
                            date = item["dt_txt"].split()[0]
                            time = item["dt_txt"].split()[1]
                            
                            # Take 12:00 forecast for each day
                            if time == "12:00:00" and date not in daily_forecasts:
                                daily_forecasts[date] = item
                        
                        for date, forecast in list(daily_forecasts.items())[:forecast_days-1]:
                            temp_day = forecast["main"]["temp"]
                            desc = forecast["weather"][0]["description"].title()
                            results.append(f"📅 **{date}:** {temp_day:.1f}°C, {desc}")
                
                prefix = self.get_pirate_response_prefix()
                return f"{prefix}\n\n" + "\n".join(results)
                
        except Exception as e:
            logger.error(f"Weather error: {str(e)}")
            return f"Blimey! The weather glass be foggy: {str(e)}"
