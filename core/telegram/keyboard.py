import datetime
import calendar
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class Calendar:
    def __init__(self, today: datetime):
        self.today = today
        self.callback_previous_month = 'callback_previous_month'
        self.callback_next_month = 'callback_next_month'
        self.callback_ignore = 'ignore'
        self.callback_close_keyboard = 'close_keyboard'
        self.close_keyboard_message = 'Закрыть'
        # next symbols
        self.symbol_previous_month = '<'
        self.symbol_next_month = '>'
        # selected days
        self.callback_select_day = 'calendar-day-'
        self.symbol_invisible = ''
        self.symbol_visible = '✅️'
        # history
        self.date_list = None

    def create_history(self, year, month, date_list):
        self.date_list = date_list
        self.callback_previous_month = 'callback_previous_month_history'
        self.callback_next_month = 'callback_next_month_history'
        self.callback_select_day = 'calendar-day-history-'
        return self.__create_calendar(year, month)

    def create_selected(self, year, month):
        self.symbol_invisible = ''
        self.symbol_visible = ''
        return self.__create_calendar(year, month)

    def __create_calendar(self, year, month):
        self.should_remove_previous(year, month)
        markup = InlineKeyboardMarkup()

        # First row - Month and Year
        markup.row(InlineKeyboardButton(calendar.month_name[month] + " " + str(year), callback_data=self.callback_ignore))
        # Second row - Week Days
        days_week = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        week = []
        for day in days_week:
            week.append(InlineKeyboardButton(day, callback_data=self.callback_ignore))
        markup.row(*week)

        my_calendar = calendar.monthcalendar(year, month)
        for week in my_calendar:
            days = []
            for day in week:
                days.append(self.check_days(day, month, year))
            markup.row(*days)

        # Add buttons
        buttons = [InlineKeyboardButton(self.symbol_previous_month, callback_data=self.callback_previous_month),
                   InlineKeyboardButton(self.close_keyboard_message, callback_data=self.callback_close_keyboard),
                   InlineKeyboardButton(self.symbol_next_month, callback_data=self.callback_next_month)]
        markup.row(*buttons)

        return markup

    def check_days(self, day, month, year):
        if day == 0 or (month == self.today.month and year == self.today.year and day < self.today.day):
            return InlineKeyboardButton(" ", callback_data=self.callback_ignore)
        elif self.date_list is None:
            return InlineKeyboardButton(str(day), callback_data=self.callback_select_day + str(day))
        else:
            return self.check_list_days(day, month, year)

    def check_list_days(self, day, month, year):
        if str(datetime.date(year=year, month=month, day=day)) in self.date_list:
            button = InlineKeyboardButton('' + self.symbol_visible, callback_data=self.callback_select_day + str(day))
        else:
            button = InlineKeyboardButton(str(day) + self.symbol_invisible, callback_data=self.callback_ignore)
        return button

    def should_remove_previous(self, year, month):
        if self.today.year == year and self.today.month == month:
            self.symbol_previous_month = ' '
            self.callback_previous_month = self.callback_ignore
        return


class Watch:
    def __init__(self):
        self.callback_ignore = 'ignore'
        # callbacks
        self.callback_data = 'calendar-time-'
        self.symbol_invisible = '️'
        self.symbol_visible = '✅️'
        self.callback_close_keyboard = 'close_keyboard'
        self.close_keyboard_message = 'Закрыть'
        # history
        self.user_time_list = None
        self.selected_date = None

    def create_history_watch(self, tselected, user_time_list):
        self.selected_date = tselected
        self.user_time_list = user_time_list
        self.callback_data = 'calendar-time-history-'
        return self.create()

    def create_note_watch(self):
        self.symbol_invisible = ''
        self.symbol_visible = ''
        self.callback_data = 'calendar-time-'
        return self.create()

    def create(self):
        times = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
            [19, 20, 21, 22, 23, 24],
        ]

        markup = InlineKeyboardMarkup()
        for row in times:
            line = []
            for i in row:
                time = i
                if i == 24:
                    time = 0

                if self.user_time_list is None:
                    line.append(InlineKeyboardButton(str(i), callback_data=self.callback_data + str(time)))
                else:
                    t_now = self.selected_date
                    t_now = t_now.replace(hour=time)
                    if str(t_now) in self.user_time_list:
                        line.append(InlineKeyboardButton(str(i) + self.symbol_visible, callback_data=self.callback_data + str(time)))
                    else:
                        line.append(InlineKeyboardButton(str(i) + self.symbol_invisible, callback_data=self.callback_ignore))

            markup.row(*line)

        # Add close button
        service_buttons = [InlineKeyboardButton(self.close_keyboard_message, callback_data=self.callback_close_keyboard)]
        markup.row(*service_buttons)

        return markup


