from dataclasses import dataclass
from typing import Dict, Optional, Union, List, Tuple

import requests
from dacite import from_dict
from caching import ttl_cache


@dataclass(unsafe_hash=True)
class LocationInfo:
    name: str
    local_names: Optional[Dict[str, str]]
    lat: float
    lon: float
    country: str
    state: Optional[str]

@dataclass
class CoordInfo:
    lat: float
    lon: float

@dataclass
class CityForecastInfo:
    id: Optional[int]
    name: str
    coord: CoordInfo
    country: str
    timezone: int
    sunrise: int
    sunset: int

@dataclass
class WeatherInfo:
    id: int
    main: str
    description: str
    icon: str


@dataclass
class CoordinateInfo:
    lat: float
    lon: float


@dataclass
class TemperatureInfo:
    temp: float
    feels_like: float
    temp_min: float
    temp_max: float
    pressure: int
    humidity: int
    sea_level: Optional[int]
    # noinspection SpellCheckingInspection
    grnd_level: Optional[int]
    temp_kf: Optional[float]

@dataclass
class WindInfo:
    speed: float
    deg: int
    gust: Optional[float]


@dataclass
class CloudInfo:
    all: int


@dataclass
class SysInfo:
    type: int
    id: int
    message: Optional[str]
    country: str
    sunrise: int
    sunset: int

@dataclass
class TotalWeatherInfo:
    coord: CoordinateInfo
    weather: List[WeatherInfo]
    base: str
    main: TemperatureInfo
    visibility: int
    wind: WindInfo
    clouds: CloudInfo
    rain: Optional[Dict]
    snow: Optional[Dict]
    dt: int
    sys: SysInfo
    timezone: int
    id: int
    name: str
    cod: int

@dataclass
class SysForecastInfo:
    pod: str

@dataclass
class ForecastMember:
    dt: int
    main: TemperatureInfo
    weather: List[WeatherInfo]
    clouds: CloudInfo
    wind: WindInfo
    rain: Optional[Dict]
    snow: Optional[Dict]
    visibility: int
    pop: float
    sys: SysForecastInfo
    dt_txt: str



@dataclass
class ForecastInfo:
    cod: str
    message: float
    cnt: int
    list: List[ForecastMember]
    city: CityForecastInfo


class Api:
    geocoding_api = 'https://api.openweathermap.org/geo/1.0/zip'
    geocoding_city_api = 'https://api.openweathermap.org/geo/1.0/direct'
    reverse_geocoding_api = 'https://api.openweathermap.org/geo/1.0/reverse'
    cur_weather_api = 'https://api.openweathermap.org/data/2.5/weather'
    cur_coords_api = 'https://ipinfo.io/loc'
    forecast_5_days_api = 'https://api.openweathermap.org/data/2.5/forecast'

    def __init__(self, app_id: str, resources: str = 'resources'):
        self.app_id = app_id
        self.resources = resources

    @staticmethod
    def locations_from_json(json: Union[Dict, List[Dict]]):
        result: List[LocationInfo] = []

        if isinstance(json, list):
            for res in json:
                result.append(from_dict(data_class=LocationInfo, data=res))
        elif isinstance(json, dict):
            res = json
            result.append(from_dict(data_class=LocationInfo, data=res))
        else:
            raise TypeError(f'unknown type got from request: {type(json)}')

        return result

    @ttl_cache()
    def locate_by_city(self, city_name: str, country: str, state_code: Optional[str] = None,
                       limit: Optional[int] = None) -> List[LocationInfo]:
        query = f'{city_name},{state_code},{country}' if state_code is not None else f'{city_name},{country}'

        req: requests.Response = requests.get(self.geocoding_city_api, params={
            'q': query,
            'limit': limit,
            'appid': self.app_id,
        })

        if len(req.json()) == 0:
            raise UserWarning

        return Api.locations_from_json(req.json())

    @ttl_cache()
    # zip_code - почтовый индекс, country - код страны
    def locate_by_zip_code(self, zip_code: str, country: str) -> List[LocationInfo]:
        # Отправляем запрос и получаем ответ, передав нужный адрес API и параметры запроса
        req: requests.Response = requests.get(self.geocoding_api, params={
            'zip': f'{zip_code},{country}',
            'appid': self.app_id,
        })

        # Если в ответе есть параметр cod, значит локация не найдена
        # В таком случае кидаем исключение
        if 'cod' in req.json():
            raise UserWarning

        # Получаем список локаций из ответа
        return Api.locations_from_json(req.json())

    @ttl_cache()
    def locate_by_coordinates(self, lat: float, lon: float, limit: Optional[int] = None) -> List[LocationInfo]:
        req: requests.Response = requests.get(self.reverse_geocoding_api, params={
            'lat': lat,
            'lon': lon,
            'limit': limit,
            'appid': self.app_id,
        })

        return Api.locations_from_json(req.json())

    def get_cur_weather_from_loc(self, location: LocationInfo, lang: str = 'ru',
                        units: str = 'metric') -> TotalWeatherInfo:
        return self.get_cur_weather(location.lat, location.lon, lang, units)

    @ttl_cache(ttl=600)
    def get_cur_weather(self, lat: float, lon: float, lang: str = 'ru',
                        units: str = 'metric') -> TotalWeatherInfo:
        req: requests.Response = requests.get(self.cur_weather_api, params={
            'lat': lat,
            'lon': lon,
            'units': units,
            'lang': lang,
            'appid': self.app_id,
        })

        info = from_dict(data_class=TotalWeatherInfo, data=req.json())

        return info

    def get_forecast_from_loc(self, location: LocationInfo, lang: str = 'ru', units: str = 'metric') -> ForecastInfo:
        return self.get_forecast(location.lat, location.lon, lang, units)

    @ttl_cache(ttl=3600)
    def get_forecast(self, lat: float, lon: float, lang: str = 'ru', units: str = 'metric') -> ForecastInfo:
        req: requests.Response = requests.get(self.forecast_5_days_api, params={
            'lat': lat,
            'lon': lon,
            'units': units,
            'lang': lang,
            'appid': self.app_id
        })

        info = from_dict(data_class=ForecastInfo, data=req.json())

        return info

    @ttl_cache(ttl=1200)
    def get_current_coordinates(self) -> Tuple[float, float]:
        coords = list(map(float, requests.get(self.cur_coords_api).text.split(',')))
        return coords[0], coords[1]
