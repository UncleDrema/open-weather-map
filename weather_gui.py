from PIL import Image
import os.path
import datetime

import caching
import ui
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QLabel, QTableWidgetItem
from PyQt6.QtGui import QPixmap

from weather_api import *


class Window:
    icons = ['01', '02', '03', '04', '09', '10', '11', '13', '50']
    pixmaps = {}

    def load_resources(self):
        if not os.path.exists(self.resources):
            os.mkdir(self.resources)
        for category in self.icons:
            for time in ['d', 'n']:
                for resolution in ['', '@2x']:
                    file_name = f'{category}{time}{resolution}.png'
                    path = os.path.join(self.resources, file_name)
                    if resolution == '@2x':
                        self.pixmaps[f'{category}{time}'] = QPixmap(path)
                    if os.path.exists(path):
                        continue
                    icon_path = f'https://openweathermap.org/img/wn/{file_name}'
                    img = Image.open(requests.get(icon_path, stream=True).raw)
                    img.save(path)

    # Инициализация графического интерфейса программы
    def init_gui(self):
        # Устанавливаем фиксированный размер окна в 800x800
        self.window.setFixedSize(800, 800)
        # Устанавливаем начальную иконку для значка погоды
        self.ui.weatherIcon.setPixmap(self.pixmaps['01d'])
        # Соединяем нажатия кнопок с функциями обработки нажатий
        self.ui.buttonZip.clicked.connect(self.on_click_zip)
        self.ui.buttonCity.clicked.connect(self.on_click_city)
        # Устанавливаем фон для значка погоды
        self.ui.weatherIcon.setStyleSheet("background-color: #828282;")
        # Соединяем выбор строк таблицы с функциями обновления информации
        self.ui.weatherTable.currentCellChanged.connect(self.on_forecast_clicked)
        self.ui.todayTable.currentCellChanged.connect(self.on_today_clicked)

    def __init__(self, app_id: str, resources: str = 'resources'):
        self.app = QApplication([])
        self.window: QMainWindow = QMainWindow()
        self.ui: ui.Ui_MainWindow = ui.Ui_MainWindow()
        self.ui.setupUi(self.window)

        self.whole_forecast = []
        self.cur_lat = 0
        self.cur_lon = 0
        self.cur_weather: Optional[Union[TotalWeatherInfo, ForecastMember]] = None
        self.noon = []
        self.api = Api(app_id)
        self.resources = resources
        self.load_resources()
        self.init_gui()

    def run(self):
        self.window.show()
        self.on_start_set_weather()
        self.app.exec()

    def on_start_set_weather(self):
        self.cur_lat, self.cur_lon = self.api.get_current_coordinates()
        self.update_all(self.cur_lat, self.cur_lon)

    def update_forecast(self, forecast_info: ForecastInfo, cur_weather: Optional[TotalWeatherInfo] = None):
        today = datetime.datetime.now()

        if cur_weather is None:
            lat, lon = self.api.get_current_coordinates()
            cur_weather = self.api.get_cur_weather(lat, lon)

        self.noon.clear()
        self.noon.append(cur_weather)
        for member in forecast_info.list:
            date = datetime.datetime.fromtimestamp(member.dt)
            if date.day != today.day and date.hour == 12:
                self.noon.append(member)
        self.whole_forecast = forecast_info.list
        for i, w in enumerate(self.noon):
            weather = w.weather[0]
            pixmap = self.pixmaps[weather.icon]
            label = QLabel(self.ui.weatherTable)
            label.setPixmap(pixmap)
            time_str = Window.utc_to_day_time(w.dt)
            desc = f'Дата и время: {time_str}\nПогода: {weather.description}\nТемпература: {w.main.temp}°C'
            self.ui.weatherTable.setCellWidget(i, 0, label)
            self.ui.weatherTable.setItem(i, 1, QTableWidgetItem(desc))

    def on_today_clicked(self, row: int, *args):
        if row == -1:
            return
        if self.cur_weather not in self.whole_forecast:
            if row == 0:
                self.update_all(self.cur_lat, self.cur_lon)
            else:
                self.update_weather_by_forecast(self.whole_forecast[row - 1])
        else:
            index = self.whole_forecast.index(self.cur_weather)
            selected = index + (row - 3)
            self.update_weather_by_forecast(self.whole_forecast[selected])

    def on_forecast_clicked(self, new_row: int, *args):
        table = self.ui.todayTable
        if new_row == 0:
            self.update_all(self.cur_lat, self.cur_lon, False)
            w = self.cur_weather
            weather = w.weather[0]
            label = QLabel(table)
            label.setPixmap(self.pixmaps[weather.icon])
            time_str = Window.utc_to_day_time(w.dt)
            desc = f'Дата и время: {time_str}\nПогода: {weather.description}\nТемпература: {w.main.temp}°C'
            table.setCellWidget(0, 0, label)
            table.setItem(0, 1, QTableWidgetItem(desc))
            for i in range(7):
                w = self.whole_forecast[i]
                weather = w.weather[0]
                label = QLabel(table)
                label.setPixmap(self.pixmaps[weather.icon])
                time_str = Window.utc_to_day_time(w.dt)
                desc = f'Дата и время: {time_str}\nПогода: {weather.description}\nТемпература: {w.main.temp}°C'
                table.setCellWidget(i + 1, 0, label)
                table.setItem(i + 1, 1, QTableWidgetItem(desc))
        else:
            self.cur_weather = self.noon[new_row]
            self.update_weather_by_forecast(self.cur_weather)
            index = self.whole_forecast.index(self.cur_weather)
            start = max(0, index - 3)
            for i in range(8):
                w = self.whole_forecast[start + i]
                weather = w.weather[0]
                label = QLabel(table)
                label.setPixmap(self.pixmaps[weather.icon])
                time_str = Window.utc_to_day_time(w.dt)
                desc = f'Дата и время: {time_str}\nПогода: {weather.description}\nТемпература: {w.main.temp}°C'
                table.setCellWidget(i, 0, label)
                table.setItem(i, 1, QTableWidgetItem(desc))

    def on_click_city(self):
        city = self.ui.inputEdit.text()
        try:
            location: LocationInfo = self.api.locate_by_city(city, 'RU')[0]
        except UserWarning:
            Window.show_message_box('Ошибка ввода города',
                                    f'Введённое вами значение "{city}" не найдено среди доступных городов!',
                                    True)
            return
        lat, lon = location.lat, location.lon
        self.update_all(lat, lon)

    def on_click_zip(self):
        zip_code = self.ui.inputEdit.text()
        try:
            location: LocationInfo = self.api.locate_by_zip_code(zip_code, 'RU')[0]
        except UserWarning:
            Window.show_message_box('Ошибка ввода почтового индекса',
                                    f'Введённое вами значение "{zip_code}" не является подходящим почтовым индексом!',
                                    True)
            return
        lat, lon = location.lat, location.lon
        self.update_all(lat, lon)

    def update_all(self, lat: float, lon: float, update_today: bool = True):
        self.cur_lat = lat
        self.cur_lon = lon
        weather_info = self.api.get_cur_weather(lat, lon)
        self.cur_weather = weather_info
        self.update_weather_total(weather_info)
        forecast_info = self.api.get_forecast(lat, lon)
        self.update_forecast(forecast_info, weather_info)
        if update_today:
            self.on_forecast_clicked(0)

    def update_weather_by_forecast(self, forecast_member: ForecastMember):
        cur_weather = forecast_member.weather[0]
        icon = cur_weather.icon
        desc = Window.weather_to_description(forecast_member)
        self.ui.weatherIcon.setPixmap(self.pixmaps[icon])
        self.ui.weatherInfoLabel.setText(desc)

    def update_weather_total(self, weather_info: TotalWeatherInfo):
        cur_weather = weather_info.weather[0]
        icon = cur_weather.icon
        desc = Window.weather_to_description(weather_info)
        main = Window.total_to_main_info(weather_info)
        self.ui.mainInfoLabel.setText(main)
        self.ui.weatherIcon.setPixmap(self.pixmaps[icon])
        self.ui.weatherInfoLabel.setText(desc)

    @staticmethod
    def show_message_box(title: str, msg: str, warning: bool = False):
        box = QMessageBox()
        box.setWindowTitle(title)
        box.setText(msg)
        if warning:
            box.setIcon(QMessageBox.Icon.Warning)
        else:
            box.setIcon(QMessageBox.Icon.Information)
        box.exec()

    @staticmethod
    def temperature_to_str(temp_info: TemperatureInfo) -> str:
        temp_str = f'Температура: {temp_info.temp}°C\nОщущается как {temp_info.feels_like}°C\nВлажность: {temp_info.humidity}%'
        return temp_str

    @staticmethod
    def weather_to_description(weather_info: Union[TotalWeatherInfo, ForecastMember]) -> str:
        weather = f'Погода: {weather_info.weather[0].description}'

        temperature = Window.temperature_to_str(weather_info.main)

        wind = f'Скорость ветра: {weather_info.wind.speed}м/c'

        return '\n'.join([weather, temperature, wind])

    @staticmethod
    def total_to_main_info(weather_info: TotalWeatherInfo) -> str:
        place = f'Местоположение: {weather_info.name},{weather_info.sys.country}'

        timezone_val = weather_info.timezone
        timezone = 'Часовой пояс: UTC {:+#2.1f}'.format(timezone_val / 3600)

        sunrise = Window.utc_to_day_time(weather_info.sys.sunrise)
        sunset = Window.utc_to_day_time(weather_info.sys.sunset)

        sun_info = f'Восход: {sunrise}\nЗакат: {sunset}'

        return '\n'.join([place, timezone, sun_info])

    @staticmethod
    @caching.ttl_cache()
    def utc_to_day_time(utc_time: int, timezone: int = 0) -> str:
        local_time = utc_time + timezone
        date = datetime.datetime.fromtimestamp(local_time)
        return date.strftime('%d/%m/%y %H:%M')
