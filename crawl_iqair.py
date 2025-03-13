from playwright.sync_api import sync_playwright
import json
from datetime import datetime
import csv
import os
import pathlib
from zoneinfo import ZoneInfo
from typing import Dict, Optional
import re

# Define cities data
CITIES = [
    {
        "name": "hanoi",
        "display_name": "Hà Nội",
        "url": "https://www.aqi.in/dashboard/vietnam/ha-noi"
    },
    {
        "name": "ho-chi-minh-city",
        "display_name": "Hồ Chí Minh",
        "url": "https://www.aqi.in/dashboard/vietnam/ho-chi-minh"
    },
    {
        "name": "da-nang",
        "display_name": "Đà Nẵng",
        "url": "https://www.aqi.in/vi/dashboard/vietnam/da-nang"
    },
    {
        "name": "hai-phong",
        "display_name": "Hải Phòng",
        "url": "https://www.aqi.in/vi/dashboard/vietnam/hai-phong"
    },
    {
        "name": "nghe-an",
        "display_name": "Nghệ An",
        "url": "https://www.aqi.in/vi/dashboard/vietnam/nghe-an"
    },
    {
        "name": "son-la",
        "display_name": "Sơn La",
        "url": "https://www.aqi.in/vi/dashboard/vietnam/son-la"
    },
    {
        "name": "bac-ninh",
        "display_name": "Bắc Ninh",
        "url": "https://www.aqi.in/vi/dashboard/vietnam/bac-ninh"
    }
]

def get_vietnam_time():
    """Get current time in Vietnam timezone (GMT+7)"""
    return datetime.now(ZoneInfo("Asia/Bangkok"))

def validate_aqi(aqi_element) -> Optional[str]:
    try:
        if not aqi_element:
            return None
        aqi_value = aqi_element.get_attribute("title")
        if not aqi_value:
            aqi_value = aqi_element.text_content().strip()
        aqi_value = re.sub(r'\D', '', aqi_value)
        if aqi_value.isdigit():
            aqi_int = int(aqi_value)
            if 0 <= aqi_int <= 500:
                return str(aqi_int)
    except (ValueError, TypeError, AttributeError):
        pass
    return None

def validate_weather_condition(condition: str) -> Optional[str]:
    if condition and isinstance(condition, str):
        # Trả về giá trị sau khi loại bỏ khoảng trắng thừa
        return condition.strip()
    return None


def validate_wind_speed(wind_element) -> Optional[str]:
    try:
        if not wind_element:
            return None
        child_spans = wind_element.query_selector_all("span")
        if child_spans:
            wind_value = child_spans[0].text_content().strip()
            wind_unit = child_spans[1].text_content().strip() if len(child_spans) > 1 else "km/h"
            wind_speed = f"{wind_value} {wind_unit}"
        else:
            wind_speed = wind_element.text_content().strip()
        if re.match(r'^\d+(\.\d+)?\s*(km/h|mph)$', wind_speed):
            if 'mph' in wind_speed:
                value = float(re.match(r'^\d+(\.\d+)?', wind_speed).group())
                km_value = value * 1.60934
                return f"{km_value:.1f} km/h"
            return wind_speed
    except (ValueError, TypeError, AttributeError):
        pass
    return None

def validate_humidity(humidity_element) -> Optional[str]:
    try:
        if not humidity_element:
            return None
        child_spans = humidity_element.query_selector_all("span")
        if child_spans:
            humidity_text = child_spans[0].text_content().strip() + "%"
        else:
            humidity_text = humidity_element.text_content().strip()
        if re.match(r'^\d{1,3}%$', humidity_text):
            return humidity_text
    except (ValueError, TypeError, AttributeError):
        pass
    return None

def validate_temperature(temp: Optional[str]) -> Optional[str]:
    try:
        if not temp:
            return None
        temp_value = float(re.sub(r'[^\d.-]', '', temp))
        if temp_value > 50:
            temp_value = (temp_value - 32) * 5 / 9
        if -50 <= temp_value <= 50:
            return f"{temp_value:.1f}°C"
    except (ValueError, TypeError):
        pass
    return None

def normalize_pollutant_name(name: str) -> str:
    name = name.lower()
    if "pm2.5" in name:
        return "pm25"
    elif "pm10" in name:
        return "pm10"
    elif "co" in name:
        return "co"
    elif "so2" in name:
        return "so2"
    elif "no2" in name:
        return "no2"
    elif "o3" in name:
        return "o3"
    else:
        return name.strip()

def extract_pollutants(page) -> Dict[str, Optional[str]]:
    pollutant_data = {}
    try:
        pollutant_elements = page.query_selector_all(".major-pollutant")
        for element in pollutant_elements:
            try:
                name_element = element.query_selector(".sensor-name")
                name_text = name_element.text_content().strip() if name_element else None
                value_element = element.query_selector("span.font-bold")
                if not value_element:
                    value_element = element.query_selector("span")
                value_text = value_element.text_content().strip() if value_element else None
                unit_element = element.query_selector(".sensor-unit")
                unit_text = unit_element.text_content().strip() if unit_element else None
                if name_text and value_text:
                    pollutant_key = normalize_pollutant_name(name_text)
                    pollutant_value = re.sub(r'[^\d.]', '', value_text)
                    if pollutant_value:
                        pollutant_data[pollutant_key] = f"{pollutant_value} {unit_text}" if unit_text else pollutant_value
            except Exception as e:
                print(f"Error extracting pollutant data: {str(e)}")
        for p in ["pm25", "pm10", "co", "so2", "no2", "o3"]:
            if p not in pollutant_data:
                pollutant_data[p] = "N/A"
    except Exception as e:
        print(f"Error extracting pollutants: {str(e)}")
    return pollutant_data

def validate_uv_index(uv_element) -> Optional[str]:
    try:
        if not uv_element:
            return None
        child_spans = uv_element.query_selector_all("span")
        if child_spans:
            uv_text = child_spans[0].text_content().strip()
        else:
            uv_text = uv_element.text_content().strip()
        if re.match(r'^\d{1,2}$', uv_text):
            uv_value = int(uv_text)
            if 0 <= uv_value <= 11:
                return str(uv_value)
    except (ValueError, TypeError, AttributeError):
        pass
    return None

def extract_weather_components(page):
    """Extract humidity, wind speed, and UV index from .component blocks"""
    weather_data = {"humidity": None, "wind_speed": None, "uv_index": None}
    try:
        components = page.query_selector_all(".component")
        for component in components:
            try:
                img_element = component.query_selector("img")
                if img_element:
                    img_alt = img_element.get_attribute("alt").strip().lower()
                    value_elements = component.query_selector_all("span")
                    if len(value_elements) > 1:
                        value_text = value_elements[1].text_content().strip()
                        if "humidity" in img_alt:
                            weather_data["humidity"] = value_text
                        elif "wind speed" in img_alt:
                            weather_data["wind_speed"] = value_text
                        elif "uv index" in img_alt:
                            weather_data["uv_index"] = value_text
            except Exception as e:
                print(f"[ERROR] extract_weather_components - {type(e).__name__}: {str(e)}")
    except Exception as e:
        print(f"[ERROR] extract_weather_components - {type(e).__name__}: {str(e)}")
    return weather_data

def extract_temperature(page) -> Optional[str]:
    """Extract temperature value from designated spans (Hình 1)"""
    temp_value_elem = page.query_selector("span.text-\\[2\\.5rem\\]")
    temp_unit_elem = page.query_selector("span.text-\\[1\\.7rem\\]")
    if temp_value_elem and temp_unit_elem:
        temp_value = temp_value_elem.text_content().strip()
        temp_unit = temp_unit_elem.text_content().strip()
        return temp_value + temp_unit
    return None

def crawl_city_data(page, city: Dict) -> Optional[Dict]:
    print(f"\nAccessing {city['display_name']} ({city['url']})...")
    try:
        page.goto(city['url'])
        page.set_default_timeout(30000)
        page.wait_for_load_state("networkidle")
        aqi_element = page.query_selector("span.font-extrabold")
        weather_condition = validate_weather_condition(page)
        if not weather_condition:
            wc_elem = page.query_selector("span.condition-text")
            weather_condition_raw = wc_elem.text_content() if wc_elem else ""
            weather_condition = validate_weather_condition(weather_condition_raw)
        temperature = extract_temperature(page)
        if not temperature:
            temp_elem = page.query_selector(".air-quality-forecast-container-weather__label")
            temperature_raw = temp_elem.text_content() if temp_elem else ""
            temperature = validate_temperature(temperature_raw)
        aqi = validate_aqi(aqi_element)
        weather_data = extract_weather_components(page)
        pollutant_data = extract_pollutants(page)
        for p in ["pm25", "pm10", "co", "so2", "no2", "o3"]:
            if p not in pollutant_data:
                pollutant_data[p] = "N/A"
        return {
            "timestamp": get_vietnam_time().isoformat(),
            "city": city['display_name'],
            "aqi": aqi,
            "weather_condition": weather_condition,
            "wind_speed": weather_data.get("wind_speed"),
            "humidity": weather_data.get("humidity"),
            "temperature": temperature,
            "uv_index": weather_data.get("uv_index"),
            **pollutant_data
        }
    except Exception as e:
        print(f"Error extracting data for {city['display_name']}: {str(e)}")
        return None

def save_to_csv(data: Dict, city_name: str):
    now = get_vietnam_time()
    result_dir = pathlib.Path(f"result/{city_name}")
    result_dir.mkdir(parents=True, exist_ok=True)
    filename = f"aqi_{city_name}_{now.year}_{now.strftime('%b').lower()}.csv"
    filepath = result_dir / filename
    headers = ["timestamp", "city", "aqi", "weather_condition", "wind_speed", "humidity", "temperature", "uv_index", "pm25", "pm10", "o3", "no2", "so2", "co"]
    file_exists = filepath.exists()
    with open(filepath, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)
    return filepath

def crawl_all_cities():
    results = []
    for city in CITIES:
        print(f"\n{'='*50}")
        print(f"Processing {city['display_name']}...")
        try:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.set_viewport_size({"width": 1280, "height": 720})
                    page.set_default_timeout(30000)
                    data = crawl_city_data(page, city)
                    if data:
                        results.append(data)
                        csv_file = save_to_csv(data, city['name'])
                        print(f"Data saved to: {csv_file}")
                    else:
                        print(f"Skipping invalid data for {city['display_name']}")
                except Exception as e:
                    print(f"Browser error for {city['display_name']}: {str(e)}")
                    continue
                finally:
                    if 'browser' in locals():
                        browser.close()
        except Exception as e:
            print(f"Playwright error for {city['display_name']}: {str(e)}")
            continue
    return results

if __name__ == "__main__":
    try:
        print("Starting IQAir data crawler...")
        print(f"Current time in Vietnam: {get_vietnam_time().strftime('%Y-%m-%d %H:%M:%S %Z')}")
        results = crawl_all_cities()
        print("\nCrawled data:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise e
