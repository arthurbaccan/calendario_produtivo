import math
import random
import threading
from tkinter import *
from tkcalendar import Calendar
from datetime import date as datetime_date
from tkinter import ttk
from enum import Enum
from datetime import datetime, timedelta
from threading import Thread
from time import sleep, time
from functools import cache
# fix for pyinstaller
import babel.numbers


class Languages(Enum):
    PT_BR = 'PT-BR'
    EN_US = 'EN-US'


# Configs:
SELECTED_LANGUAGE = Languages.EN_US
COLOR_EVENT_1_HEX = '#FFD16E'
COLOR_EVENT_2_HEX = '#52DEBF'
COLOR_EVENT_3_HEX = '#7A67F5'
CALENDAR_FONT_SIZE = 20

global selected_event_label
global selected_date
global day_label
event_label_selected: bool = False
event_buttons_frame: bool | Frame = False
do_or_not_event_button: bool | Frame = False
remove_event_button: bool | Frame = False
separator_event_frame: bool | Frame = False
first_time: bool = True
selected_event_type = 'Padrão'


# this class modifies the tkcalendar, so it shows the events in the calendar squares, instead of in a pop-up
class Agenda(Calendar):

    def __init__(self, master=None, **kw):
        Calendar.__init__(self, master, **kw)
        # change a bit the options of the labels to improve display
        for i, row in enumerate(self._calendar):
            for j, label in enumerate(row):
                self._cal_frame.rowconfigure(i + 1, uniform=1)
                self._cal_frame.columnconfigure(j + 1, uniform=1)
                label.configure(justify="center", anchor="n", padding=(1, 4))

    # formats the text, so it fits in the calendar square(label with date inside the square)
    def format_calevent_text(self, ev_ids, label, date=None):
        text_from_calevents = [self.calevents[ev]['text'] for ev in ev_ids]
        text_calevents_string = ''
        len_calevents_list = len(text_from_calevents)
        label.configure(wraplength=label.winfo_width())

        # waits on a new thread for the labels to be loaded and then the events can be properly loaded
        # (widgets sizes cant be measured before it loads)
        def reshow_event():
            if not date:
                return False
            while label.winfo_width() <= 1:
                sleep(0.5)
            self._show_event(date)
            return True

        if label.winfo_width() <= 1:
            thread = Thread(target=reshow_event)
            thread.start()

        count = 0
        for event in text_from_calevents:
            count += 1
            text_calevents_string += event
            if len_calevents_list != count:
                text_calevents_string += '\n'

        max_characters = (label.winfo_width() + label.winfo_height()) / (CALENDAR_FONT_SIZE / 3)
        max_characters = int(max_characters - 1)
        # print('width:', label.winfo_width())
        # print('height:', label.winfo_height())
        # print(max_characters)
        # print('--' * 20)
        # print(text_calevents_string[:max_characters] + '...')
        return text_calevents_string[:max_characters] + '...'

    def _display_days_without_othermonthdays(self):
        year, month = self._date.year, self._date.month

        cal = self._cal.monthdays2calendar(year, month)
        while len(cal) < 6:
            cal.append([(0, i) for i in range(7)])

        week_days = {i: 'normal.%s.TLabel' % self._style_prefixe for i in
                     range(7)}  # style names depending on the type of day
        week_days[self['weekenddays'][0] - 1] = 'we.%s.TLabel' % self._style_prefixe
        week_days[self['weekenddays'][1] - 1] = 'we.%s.TLabel' % self._style_prefixe
        _, week_nb, d = self._date.isocalendar()
        if d == 7 and self['firstweekday'] == 'sunday':
            week_nb += 1
        modulo = max(week_nb, 52)
        for i_week in range(6):
            if i_week == 0 or cal[i_week][0][0]:
                self._week_nbs[i_week].configure(text=str((week_nb + i_week - 1) % modulo + 1))
            else:
                self._week_nbs[i_week].configure(text='')
            for i_day in range(7):
                day_number, week_day = cal[i_week][i_day]
                style = week_days[i_day]
                label = self._calendar[i_week][i_day]
                label.state(['!disabled'])
                if day_number:
                    txt = str(day_number)
                    label.configure(text=txt, style=style)
                    date = self.date(year, month, day_number)
                    if date in self._calevent_dates:
                        ev_ids = self._calevent_dates[date]
                        i = len(ev_ids) - 1
                        while i >= 0 and not self.calevents[ev_ids[i]]['tags']:
                            i -= 1
                        if i >= 0:
                            tag = self.calevents[ev_ids[i]]['tags'][-1]
                            label.configure(style='tag_%s.%s.TLabel' % (tag, self._style_prefixe))
                        # modified lines:
                        text_from_calevents = self.format_calevent_text(ev_ids, label)
                        text = '%s\n' % day_number + text_from_calevents
                        label.configure(text=text)
                else:
                    label.configure(text='', style=style)

    def _show_event(self, date):
        """Display events on date if visible."""
        w, d = self._get_day_coords(date)
        if w is not None:
            label = self._calendar[w][d]
            if not label.cget('text'):
                # this is another month's day and showothermonth is False
                return
            ev_ids = self._calevent_dates[date]
            i = len(ev_ids) - 1
            while i >= 0 and not self.calevents[ev_ids[i]]['tags']:
                i -= 1
            if i >= 0:
                tag = self.calevents[ev_ids[i]]['tags'][-1]
                label.configure(style='tag_%s.%s.TLabel' % (tag, self._style_prefixe))
            # modified lines:
            text_from_calevents = self.format_calevent_text(ev_ids, label, date)
            text = '%s\n' % date.day + text_from_calevents
            label.configure(text=text)

    def _on_click(self, event):
        """Select the day on which the user clicked."""
        if self._properties['state'] == 'normal':
            global day_label
            label = event.widget
            day_label = label
            if "disabled" not in label.state():
                day = label.cget("text")
                day = day[:2]
                style = label.cget("style")
                if style in ['normal_om.%s.TLabel' % self._style_prefixe, 'we_om.%s.TLabel' % self._style_prefixe]:
                    if label in self._calendar[0]:
                        self._prev_month()
                    else:
                        self._next_month()
                if day:
                    day = int(day)
                    year, month = self._date.year, self._date.month
                    self._remove_selection()
                    self._sel_date = self.date(year, month, day)
                    self._display_selection()
                    if self._textvariable is not None:
                        self._textvariable.set(self.format_date(self._sel_date))
                    self.event_generate("<<CalendarSelected>>")


def main():
    text_by_language = {
        Languages.EN_US: ['Events', 'Event name:', 'Event type:', 'Event Timespan:', 'Start:', 'End:',
                          'Total Duration(Hours):', 'Create event', 'Remove event in selected day', 'Remove event',
                          'Read ', ' pages ', 'Work ', ' hours on ', 'Total Pages:', "Book's Name:", 'Language:'],
        Languages.PT_BR: ['Eventos', 'Nome do evento:', 'Tipo de evento:', 'Duração do evento:', 'Início:',
                          'Fim:', 'Horas Totais:', 'Criar evento', 'Remover evento nesse dia', 'Remover evento',
                          'Ler ', ' páginas ', 'Trabalhar ', ' horas em ', 'Páginas Totais:', 'Nome do Livro:',
                          'Língua']

    }

    # this dict relates the labels objects and their event ids
    # structure: event_id: label object(tkinter label)
    event_labels = {}
    # this dict relates one event to another, just like in a database
    # structure: event_id: {'number': event_number, 'date': event_date(datetime)}
    event_id_and_associated_events_number: {int: (datetime, int)} = {}
    # event ids from the events of type read book('ler livro') and the total number of pages of the book
    # structure: event_id: total_pages
    read_book_event_ids_and_pages = {}
    # event ids from the events of type assignment('trabalho') and the total number of hours of the assignment
    # structure: event_id: total_hours
    assignment_event_ids_and_hours = {}
    # list with the event dates and numbers
    # structure: some number: {'number': event_number, 'date': event_date(datetime.date)}
    event_number_date_to_delete: [[int, datetime]] = []

    # creates all main widgets, the ones that appear when the software
    # is opened(labels_frame and the widgets in it are created only once)
    def create_main_widgets():
        global first_time
        if first_time:
            global labels_frame
        global separator_frame
        global entries_frame
        global event_type_option_menu_frame
        global start_end_event_frame
        global pages_hours_total_frame
        global buttons_frame
        if first_time:
            global event_description_label
        global event_name_label
        global event_name_entry
        global event_type_label
        global event_types_list
        global event_types_var
        global event_type_option_menu
        global event_duration_label
        global event_start_label
        global start_event_var
        global event_start_entry
        global event_finish_label
        global end_event_var
        global event_end_entry
        global pages_hours_label_var
        global pages_hours_total_label
        global pages_hours_total_entry
        global add_event_button
        global main_widgets_list
        main_widgets_list = []

        if first_time:
            labels_frame = ttk.Frame(frame)
            labels_frame.pack(expand=False, fill='x', side='top')

        separator_frame = Frame(frame, background='gray', height=15)
        separator_frame.pack(expand=False, fill='x', side='top', pady=10)
        main_widgets_list.append(separator_frame)

        entries_frame = ttk.Frame(frame)
        entries_frame.pack(expand=False, fill='x', side='top')
        main_widgets_list.append(entries_frame)

        event_type_option_menu_frame = ttk.Frame(frame, height=100)
        event_type_option_menu_frame.pack_propagate(False)
        event_type_option_menu_frame.pack(expand=False, fill='both', side='top')
        main_widgets_list.append(event_type_option_menu_frame)

        start_end_event_frame = ttk.Frame(frame)
        start_end_event_frame.pack(expand=False, fill='both', side='top')
        main_widgets_list.append(start_end_event_frame)

        pages_hours_total_frame = ttk.Frame(frame)
        pages_hours_total_frame.pack(expand=False, fill='both', side='top')
        main_widgets_list.append(pages_hours_total_frame)

        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(expand=False, fill='both', side='top')
        main_widgets_list.append(buttons_frame)

        # Widgets in order of appearance(top to bottom, mostly; same as the frames)
        if first_time:
            event_description_label = ttk.Label(labels_frame, justify='center', anchor='center', font='Arial 30',
                                                text=text_by_language[SELECTED_LANGUAGE][0])
            event_description_label.pack(expand=False, fill='x', side='top', pady=20)

        event_name_label = ttk.Label(entries_frame, text=text_by_language[SELECTED_LANGUAGE][1], font='Arial 15',
                                     justify='center',
                                     anchor='center')
        event_name_label.pack(expand=False, fill='x', side='top')
        main_widgets_list.append(event_name_label)

        event_name_entry = ttk.Entry(entries_frame)
        event_name_entry.pack(expand=False, fill='both', side='top')
        main_widgets_list.append(event_name_entry)

        event_type_label = ttk.Label(event_type_option_menu_frame, text=text_by_language[SELECTED_LANGUAGE][2],
                                     font='Arial 15',
                                     justify='center', anchor='center')
        event_type_label.pack(expand=False, fill='x', side='top')
        main_widgets_list.append(event_type_label)

        # event type var
        event_types_var = StringVar(event_type_option_menu_frame, EventTypes.PADRAO.value)
        event_types_list = [EventTypes.PADRAO.value, EventTypes.LER_LIVRO.value, EventTypes.TRABALHO.value]

        event_type_option_menu = OptionMenu(event_type_option_menu_frame, event_types_var, *event_types_list,
                                            command=event_type_changed)
        event_type_option_menu.pack(expand=False, side='top')
        main_widgets_list.append(event_type_option_menu)

        event_duration_label = Label(start_end_event_frame, text=text_by_language[SELECTED_LANGUAGE][3],
                                     font='Arial 15',
                                     justify='center', anchor='center')
        event_duration_label.pack(expand=False, fill='x', side='top')
        main_widgets_list.append(event_duration_label)

        event_start_label = Label(start_end_event_frame, text=text_by_language[SELECTED_LANGUAGE][4], font='Arial 15',
                                  justify='center', anchor='center')
        event_start_label.pack(expand=False, fill='x', side='top')
        main_widgets_list.append(event_start_label)

        if SELECTED_LANGUAGE == Languages.PT_BR:
            start_event_var = StringVar(start_end_event_frame, datetime.now().strftime("%d/%m/%Y"))
        elif SELECTED_LANGUAGE == Languages.EN_US:
            start_event_var = StringVar(start_end_event_frame, datetime.now().strftime("%m/%d/%Y"))

        event_start_entry = ttk.Entry(start_end_event_frame, textvariable=start_event_var)
        event_start_entry.pack(expand=False, fill='both', side='top')
        main_widgets_list.append(event_start_entry)

        event_finish_label = Label(start_end_event_frame, text=text_by_language[SELECTED_LANGUAGE][5], font='Arial 15',
                                   justify='center', anchor='center')
        event_finish_label.pack(expand=False, fill='x', side='top')
        main_widgets_list.append(event_finish_label)

        if SELECTED_LANGUAGE == Languages.PT_BR:
            end_event_var = StringVar(start_end_event_frame, datetime.now().strftime("%d/%m/%Y"))
        if SELECTED_LANGUAGE == Languages.EN_US:
            end_event_var = StringVar(start_end_event_frame, datetime.now().strftime("%m/%d/%Y"))

        event_end_entry = ttk.Entry(start_end_event_frame, textvariable=end_event_var)
        event_end_entry.pack(expand=False, fill='both', side='top')
        main_widgets_list.append(event_end_entry)

        pages_hours_label_var = StringVar(pages_hours_total_frame, text_by_language[SELECTED_LANGUAGE][6])
        pages_hours_total_label = ttk.Label(pages_hours_total_frame, font='Arial 15',
                                            justify='center', anchor='center', textvariable=pages_hours_label_var)
        pages_hours_total_label.pack(expand=False, fill='x', side='top')
        main_widgets_list.append(pages_hours_total_label)

        pages_hours_total_entry = ttk.Entry(pages_hours_total_frame)
        pages_hours_total_entry.pack(expand=False, fill='both', side='top')
        main_widgets_list.append(pages_hours_total_entry)

        add_event_button = ttk.Button(buttons_frame, text=text_by_language[SELECTED_LANGUAGE][7],
                                      command=add_event_pressed_handler)
        add_event_button.pack(expand=False, fill='x', side='top')
        main_widgets_list.append(add_event_button)

        first_time = False

        # creates a new thread and waits for the widgets to load, so the sizes can be set correctly
        def set_labels_frame_winfo_width():
            global labels_frame_winfo_width
            while labels_frame.winfo_width() < 10:
                sleep(1)
            labels_frame_winfo_width = labels_frame.winfo_width()
            return True

        thread = threading.Thread(target=set_labels_frame_winfo_width)
        thread.start()

    # destroys all widgets in the main widgets, except for the labels_frame and the widgets in it
    def destroy_main_widgets():
        for item in main_widgets_list:
            item.destroy()

    # destroys all the labels with the event names
    def destroy_all_event_labels():
        for key in event_labels:
            event_labels[key].destroy()
        event_labels.clear()

    # gets the id from the event the label is referring to.
    # It searches through the list of all event labels and their related event_ids
    def get_event_id_from_event_labels_list(label):
        for key in event_labels:
            if event_labels[key] == label:
                return key

    # removes the widgets in the menu of the event options(panel with the buttons to remove the event), if they exist
    def remove_event_label_widgets():
        global event_label_selected
        event_label_selected = False
        if type(event_buttons_frame) == Frame:
            event_buttons_frame.destroy()
        if type(do_or_not_event_button) == Button:
            do_or_not_event_button.destroy()
        if type(remove_event_button) == Button:
            remove_event_button.destroy()
        if type(separator_event_frame) == Frame:
            separator_event_frame.destroy()

    # creates the widgets that appear when you click on a label in the menu
    def create_event_label_widgets():
        global event_label_selected
        event_label_selected = True
        destroy_main_widgets()

        # widgets that show up when you select an event:
        global event_buttons_frame
        global do_or_not_event_button
        global remove_event_button
        global separator_event_frame
        global labels_frame
        global event_description_label

        separator_event_frame = Frame(frame, background='gray', height=15)
        separator_event_frame.pack(expand=False, fill='x', side='top', pady=10)

        event_buttons_frame = Frame(frame)
        event_buttons_frame.pack(expand=False, fill='x', side='top')

        do_or_not_event_button = Button(event_buttons_frame, textvariable=event_do_or_not_button_text,
                                        command=do_or_not_button_clicked)
        do_or_not_event_button.pack(expand=False, fill='x', side='top')

        remove_event_button = Button(event_buttons_frame, text=text_by_language[SELECTED_LANGUAGE][9], background='Red',
                                     command=remove_event_and_related)
        remove_event_button.pack(side='top', expand=False, fill="x")

    # get all the event_ids that are related to the event from the selected label. For example, if the user selects
    # a label from a book reading event, its gets the event_ids from all the events that are from that same book
    def get_selected_label_related_events() -> [int]:
        event_id = get_event_id_from_event_labels_list(selected_event_label)
        event_number: int = event_id_and_associated_events_number[event_id]['number']
        events_ids_related_to_event: [int] = get_events_related_to(event_number)
        return events_ids_related_to_event

    # removes the event and all the other events that are from the same book/assignment/default event
    def remove_event_and_related():
        events_ids_related_to_event = get_selected_label_related_events()
        for event_id in events_ids_related_to_event:
            remove_event(event_id)

    # creates a list with all events that share the same event number
    def create_list_with_same_events_number(event_number: int, events_list) -> list:
        list_of_events_with_same_number = []
        for event in events_list:
            if event['number'] == event_number:
                list_of_events_with_same_number += event,
        return list_of_events_with_same_number

    # splits the string correctly to get the event name written in the label with the book name and number of pages
    def get_event_book_name(label_text: str):
        words = label_text.split(' ')
        return words[3:]

    # splits the string correctly to get the event name written in the label with the assignment
    # name and number of pages
    def get_event_assignment_name(label_text: str):
        words = label_text.split(' ')
        return words[4:]

    def is_event_in_events_to_delete_list(event_number: int, event_date: datetime.date):
        for event_id_deleted in event_number_date_to_delete:
            if event_number == event_id_deleted['number'] and event_date == event_id_deleted['date']:
                return True
        return False

    def place_event_in_events_to_delete_list(event_number: int, event_date: datetime.date):
        parameters = {'number': event_number, 'date': event_date}
        event_number_date_to_delete.append(parameters)

    # gets the start and end dates, but also searches in the deleted events list,
    # so it can get the original start and end dates(doesn't account for the specific event days the user deleted)
    def get_start_end_including_deleted_events(previous_start, previous_end, events_deleted_list: list):
        dates_list = []

        for date in get_dates(previous_start, previous_end):
            dates_list += date,

        for event in events_deleted_list:
            dates_list += event['date'],
        start = min(dates_list)
        end = max(dates_list)
        return start, end

    # deletes/removes all the events in the events to delete list
    @cache
    def remove_events_in_events_to_delete_list_from_calendar():
        for event in event_number_date_to_delete:
            event_id = get_event_id_from_event_number_and_date(event['number'], event['date'])
            remove_event(event_id)

    # deletes a specific day of the event, not all the dates,
    # and redistributes the number of pages and hours to the remaining days
    def dont_do_event_in_selected_day():
        event_id = get_event_id_from_event_labels_list(selected_event_label)
        event_number = get_event_number_from_id(event_id)
        events_ids_related_to_event = get_events_related_to(event_number)
        start, end = get_start_end_event_from(events_ids_related_to_event)
        event_label_text: str = selected_event_label.cget('text')
        event_date: datetime = get_event_date_from_id(event_id)

        event_id_is_in_list = is_event_in_events_to_delete_list(event_number, event_date)

        # checks if the event the user clicked to delete is already in the events to delete list
        if not event_id_is_in_list:
            place_event_in_events_to_delete_list(event_number, event_date)
        events_deleted_related_to_selected_event = create_list_with_same_events_number(event_number,
                                                                                       event_number_date_to_delete)

        start, end = get_start_end_including_deleted_events(start, end, events_deleted_related_to_selected_event)

        days_less_total = len(events_deleted_related_to_selected_event)
        remove_event_and_related()

        # handling of each event type
        if selected_event_type == EventTypes.LER_LIVRO.value:
            event_name = get_event_book_name(event_label_text)
            event_name = str.join(" ", event_name)
            total_pages = read_book_event_ids_and_pages[events_ids_related_to_event[0]]
            event_ler_livro(start, end, days_less_total, total_pages, event_name, True, event_number)
        elif selected_event_type == EventTypes.TRABALHO.value:
            event_name = get_event_assignment_name(event_label_text)
            event_name = str.join(" ", event_name)
            total_hours = assignment_event_ids_and_hours[events_ids_related_to_event[0]]
            event_trabalho(start, end, event_name, days_less_total, event_number, total_hours)
        elif selected_event_type == EventTypes.PADRAO.value:
            event_name = event_label_text
            event_padrão(start, end, event_name, event_number)

        remove_events_in_events_to_delete_list_from_calendar()

    # I added this function in case I want to add more functionalities to the button later
    def do_or_not_button_clicked():
        dont_do_event_in_selected_day()

    # fires when the user selects a label from the
    # events list(at the side GUI, with the list of the events in the selected day)
    def select_event_label(event):
        global selected_event_label
        global event_label_selected
        if event_label_selected:
            remove_event_label_widgets()
            selected_event_label.configure(background=frame.cget('background'))
            agenda.selection_set(None)
            return False
        selected_event_label = event.widget
        selected_event_label.configure(background='Gray')
        event_id: int = get_event_id_from_event_labels_list(selected_event_label)
        event_tags: list = agenda.calevent_cget(event_id, "tags")
        event_type_changed(event_tags[0])
        create_event_label_widgets()

    # creates the labels with the name and text of each even in the selected day
    def create_event_labels_in_frame() -> None:
        agenda_selected_date = agenda.selection_get()
        event_ids = agenda.get_calevents(agenda_selected_date)
        for event_id in event_ids:
            label = Label(labels_frame, text=agenda.calevent_cget(event_id, 'text'), justify='center', anchor='center',
                          font=f'Arial {str(CALENDAR_FONT_SIZE)}', wraplength=labels_frame_winfo_width)
            label.pack(side='top', expand=False, fill="x")
            label.bind("<Button-1>", select_event_label)
            event_labels[event_id] = label

    # removes the event text(not the date) from the label inside the calendar squares
    def remove_event_text_from_label():
        text = day_label.cget('text')[:2]
        day_label.configure(text=text)

    # removes an event from the events list and uses the calevent_remove function to remove it from the calendar
    def remove_event(event_id):
        agenda.calevent_remove(event_id)
        destroy_all_event_labels()
        create_event_labels_in_frame()
        if len(event_labels) == 0:
            remove_event_text_from_label()
        remove_event_label_widgets()
        try:
            event_id_and_associated_events_number.pop(event_id)
        except KeyError:
            pass
        agenda._display_days_without_othermonthdays()

    # gets the start and end of an event given a list of dates that event is at.
    def get_start_end_event_from(event_ids: [int]) -> (datetime, datetime):
        start_date: datetime.date = agenda.calevent_cget(min(event_ids), 'date')
        end_date: datetime.date = agenda.calevent_cget(max(event_ids), 'date')
        return start_date, end_date

    def get_start_end_event_from_event_date_var_text() -> tuple[datetime, datetime]:
        start_date_string = start_event_var.get()
        end_date_string = end_event_var.get()
        if SELECTED_LANGUAGE == Languages.PT_BR:
            start_year = int(start_date_string[6:])
            start_month = int(start_date_string[3:5])
            start_day = int(start_date_string[0:2])
            end_year = int(end_date_string[6:])
            end_month = int(end_date_string[3:5])
            end_day = int(end_date_string[0:2])
            return datetime(year=start_year, day=start_day, month=start_month), \
                datetime(year=end_year, day=end_day, month=end_month)
        elif SELECTED_LANGUAGE == Languages.EN_US:
            start_year = int(start_date_string[6:])
            start_day = int(start_date_string[3:5])
            start_month = int(start_date_string[0:2])
            end_year = int(end_date_string[6:])
            end_day = int(end_date_string[3:5])
            end_month = int(end_date_string[0:2])
            return datetime(year=start_year, day=start_day, month=start_month), \
                datetime(year=end_year, day=end_day, month=end_month)

    # calls the correct function for each event type
    def event_type_handler():
        event_type = event_types_var.get()

        start, end = get_start_end_event_from_event_date_var_text()

        if event_type == EventTypes.LER_LIVRO.value:
            event_ler_livro(start, end)
        elif event_type == EventTypes.PADRAO.value:
            event_padrão(start, end)
        elif event_type == EventTypes.TRABALHO.value:
            event_trabalho(start, end)

    # gets all dates in between a start and end date
    def get_dates(start: datetime, end: datetime):
        selected_day = start
        days_list = [start]
        while selected_day != end:
            selected_day = selected_day + timedelta(days=1)
            days_list.append(selected_day)
        return days_list

    def calculate_pages_per_day(start_date: datetime | datetime_date, end_date: datetime | datetime_date,
                                total_pages: float) -> tuple[int, float]:
        try:
            delta = end_date.date() - start_date.date()
        except AttributeError:
            # this codes make so the start and end date can be a datetime.datetime object
            delta = end_date - start_date
        pages_per_day = int(math.ceil(total_pages / (delta.days + 1)))
        last_day_pages = int(total_pages - pages_per_day * delta.days)
        return pages_per_day, last_day_pages

    # gets the events related to that one by comparing the event numbers and seeing if they are the same.
    # It searches in the event ids list
    def get_events_related_to(event_number: int) -> [int]:
        related_events_list = []
        for key, other_event in event_id_and_associated_events_number.items():
            if event_number == other_event['number']:
                related_events_list.append(key)
        return related_events_list

    # gets the event_id by comparing its event number and date and finding a match in the event ids list
    def get_event_id_from_event_number_and_date(event_number: int, date: datetime.date):
        for key, event in event_id_and_associated_events_number.items():
            if event['number'] == event_number and event['date'] == date:
                return key

    def get_event_number_from_id(event_id: int) -> int:
        return event_id_and_associated_events_number[event_id]['number']

    def get_event_date_from_id(event_id: int) -> datetime:
        return event_id_and_associated_events_number[event_id]['date']

    # generates a random event number and checks if it is already used
    def generate_event_number():
        event_number = random.randint(1, 1000000000000000000000)
        try:
            for key, event in event_id_and_associated_events_number.items():
                while key == event_number:
                    event_number = random.randint(1, 1000000000000000000000)
        except TypeError:
            print('Type error')
        return event_number

    def add_event_to_event_id_and_associated_events_dict(event_id: int, event_number):
        event_date = agenda.calevent_cget(event_id, 'date')
        event_id_and_associated_events_number[event_id] = {'number': event_number, 'date': event_date}

    # handles the creation of an event of the type "ler livro"(translation: read book)
    def event_ler_livro(start: datetime, end: datetime, days_less=0, total_pages_override=None,
                        event_name_override=None, can_read_more_pages_than_total=False, event_number=None):
        if not total_pages_override:
            total_pages = float(pages_hours_total_entry.get())
        else:
            total_pages = total_pages_override
        if not event_name_override:
            event_name = event_name_entry.get()
        else:
            event_name = event_name_override
        end_days = end - timedelta(days=days_less)
        pages_per_day, last_day_pages = calculate_pages_per_day(start, end_days, total_pages)
        all_dates = get_dates(start, end)
        pages_read = 0
        if not event_number:
            event_number = generate_event_number()

        for date in all_dates:
            if not date == all_dates[len(all_dates) - 1]:
                event_id = agenda.calevent_create(date,
                                                  text_by_language[SELECTED_LANGUAGE][10] + str(pages_per_day) +
                                                  text_by_language[SELECTED_LANGUAGE][11] + event_name,
                                                  "ler_livro")
                read_book_event_ids_and_pages[event_id] = total_pages
                add_event_to_event_id_and_associated_events_dict(event_id, event_number)
            else:
                event_id = agenda.calevent_create(date,
                                                  text_by_language[SELECTED_LANGUAGE][10] + str(last_day_pages) +
                                                  text_by_language[SELECTED_LANGUAGE][11] + event_name,
                                                  "ler_livro")
                add_event_to_event_id_and_associated_events_dict(event_id, event_number)
            pages_read += pages_per_day
            if pages_read > total_pages and not can_read_more_pages_than_total:
                break

    def calculate_hours_per_day(start_date: datetime, end_date: datetime, total_hours: float) -> float:
        try:
            delta = end_date.date() - start_date.date()
        except AttributeError:
            delta = end_date - start_date
        hours_per_day = total_hours / (delta.days + 1)
        return hours_per_day

    # handles the creation of an event of the type "padrão"(translation: default)
    def event_padrão(start, end, override_event_name: str = None, override_event_number: int = None):
        all_dates = get_dates(start, end)
        if override_event_name:
            event_name = override_event_name
        else:
            event_name = event_name_entry.get()
        if override_event_number:
            event_number = override_event_number
        else:
            event_number = generate_event_number()

        for date in all_dates:
            if not date == all_dates[len(all_dates) - 1]:
                event_id = agenda.calevent_create(date, event_name, "padrão")
                add_event_to_event_id_and_associated_events_dict(event_id, event_number)
            else:
                event_id = agenda.calevent_create(date, event_name, "padrão")
                add_event_to_event_id_and_associated_events_dict(event_id, event_number)

    # handles the creation of an event of the type "trabalho"(translation: assignment)
    def event_trabalho(start, end, override_event_name: str = None, days_less=0, override_event_number: int = None,
                       total_hours_override: int = None):
        if override_event_name:
            event_name = override_event_name
        else:
            event_name = event_name_entry.get()
        all_dates = get_dates(start, end)
        end = end - timedelta(days=days_less)
        if total_hours_override:
            total_hours = total_hours_override
        else:
            total_hours = float(pages_hours_total_entry.get())
        hours_per_day = calculate_hours_per_day(start, end, total_hours)
        if override_event_number:
            event_number = override_event_number
        else:
            event_number = generate_event_number()

        for date in all_dates:
            event_id = agenda.calevent_create(date,
                                              text_by_language[SELECTED_LANGUAGE][12] + str(
                                                  round(hours_per_day, 2)) + text_by_language[SELECTED_LANGUAGE][13]
                                              + event_name, "trabalho")
            assignment_event_ids_and_hours[event_id] = total_hours
            add_event_to_event_id_and_associated_events_dict(event_id, event_number)

    # updates the UI text when the event type changes
    def event_type_changed(event_type):
        global selected_event_type
        if event_type == EventTypes.LER_LIVRO.value or event_type == 'ler_livro':  # 'ler_livro' = read book
            selected_event_type = EventTypes.LER_LIVRO.value
            pages_hours_label_var.set(text_by_language[SELECTED_LANGUAGE][14])  # 'Páginas Totais' = total pages
            event_name_label.configure(text=text_by_language[SELECTED_LANGUAGE][15])  # 'Nome do livro' = book name
            # do_or_not_event_button["state"] = "enabled"
        elif event_type == EventTypes.TRABALHO.value or event_type == 'trabalho':  # trabalho = assignment
            selected_event_type = EventTypes.TRABALHO.value
            pages_hours_label_var.set(text_by_language[SELECTED_LANGUAGE][6])  # 'Horas Totais' = total hours
            event_name_label.configure(text=text_by_language[SELECTED_LANGUAGE][1])
            # do_or_not_event_button["state"] = "enabled"
        elif event_type == EventTypes.PADRAO.value or event_type == 'padrão':  # padrão = default
            selected_event_type = EventTypes.PADRAO.value
            pages_hours_label_var.set(text_by_language[SELECTED_LANGUAGE][6])
            event_name_label.configure(text=text_by_language[SELECTED_LANGUAGE][1])  # 'Horas Totais' = total hours
            # do_or_not_event_button["state"] = "disabled"

    # updates the GUI and sets the start date as the selected day's date
    def clicked_day_handler(_event) -> None:
        remove_event_label_widgets()
        destroy_main_widgets()
        create_main_widgets()
        if SELECTED_LANGUAGE == Languages.PT_BR:
            start_event_var.set(agenda.selection_get().strftime("%d/%m/%Y"))
        elif SELECTED_LANGUAGE == Languages.EN_US:
            start_event_var.set(agenda.selection_get().strftime("%m/%d/%Y"))
        get_start_end_event_from_event_date_var_text()
        destroy_all_event_labels()
        create_event_labels_in_frame()

    # handles the add event button("Adicionar evento = add/create event")
    def add_event_pressed_handler() -> None:
        event_type_handler()
        destroy_all_event_labels()
        create_event_labels_in_frame()

    class EventTypes(Enum):
        if SELECTED_LANGUAGE == Languages.PT_BR:
            LER_LIVRO = 'Ler livro'  # ler livro = read book
            PADRAO = 'Padrão'  # Padrão = default
            TRABALHO = 'Trabalho'  # trabalho = assignment
        elif SELECTED_LANGUAGE == Languages.EN_US:
            LER_LIVRO = 'Read book'
            PADRAO = 'Default'
            TRABALHO = 'Assignment'

    # Configuring the root window
    root = Tk()
    root.geometry("%dx%d+-10+0" % (root.winfo_screenwidth(), root.winfo_screenheight()))

    root.title('Calendário Produtivo')

    if SELECTED_LANGUAGE == Languages.PT_BR:
        agenda = Agenda(root, selectmode='day', font="Arial 20", showweeknumbers=False, showothermonthdays=False,
                        locale="pt_BR", background='black')
    elif SELECTED_LANGUAGE == Languages.EN_US:
        agenda = Agenda(root, selectmode='day', font="Arial 20", showweeknumbers=False, showothermonthdays=False,
                        locale="en_US", background='black')
    agenda.pack(expand=True, fill="both", side='left')

    # All the widgets from the side menu are parented to the frame
    frame = Frame(root, width=root.winfo_width() / 4, height=root.winfo_height() / 4)
    frame.pack_propagate(False)
    frame.pack(expand=False, fill='y', side='right')

    event_do_or_not_button_text = StringVar(frame, text_by_language[SELECTED_LANGUAGE][8])

    create_main_widgets()

    # tags and their colors(HEX)
    agenda.tag_config("padrão", background=COLOR_EVENT_1_HEX)
    agenda.tag_config("ler_livro", background=COLOR_EVENT_2_HEX)
    agenda.tag_config("trabalho", background=COLOR_EVENT_3_HEX)

    agenda.bind("<<CalendarSelected>>", clicked_day_handler)

    agenda.selection_set(datetime_date.today())

    root.mainloop()


if __name__ == '__main__':
    main()
