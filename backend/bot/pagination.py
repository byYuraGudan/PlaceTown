from django.core.paginator import Paginator
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from backend.bot.keyboards import build_menu

PAGE_SIZE = 10
MAX_PAGE_SIZE = 50


class BasePaginator:
    _keyboard = None
    first_page_label = '« {}'
    previous_page_label = '‹ {}'
    next_page_label = '{} ›'
    last_page_label = '{} »'
    current_page_label = '·{}·'

    def __init__(self, data, page: int = 1, page_size: int = PAGE_SIZE, title_pattern='{name}'):
        self._data = data

        assert page > 0, 'Page must more than 0'
        self._page = page

        if page_size is not None:
            assert page_size <= MAX_PAGE_SIZE, f'Page size must less MAX_PAGE_SIZE = {MAX_PAGE_SIZE}'
        self._page_size = page_size or PAGE_SIZE
        self._paginator = Paginator(data, self._page_size)
        self._title_pattern = title_pattern

    @property
    def data(self):
        return self._paginator.get_page(self._page).object_list

    @property
    def page_count(self):
        return self._paginator.num_pages


class CallbackPaginator(BasePaginator):

    def __init__(
            self, data, callback, page_callback,
            page: int = 1, page_size: int = PAGE_SIZE,
            title_pattern='{name}', callback_data_keys=None
    ):

        super(CallbackPaginator, self).__init__(data, page, page_size, title_pattern)
        self._page_callback = page_callback
        self._callback_data_keys = callback_data_keys or ['id']
        self._callback = callback

    def _build(self):
        keyboard_page = list()
        if self.page_count == 1:
            self._keyboard_page = list()
        elif self.page_count <= 5:
            for page in self._paginator.page_range:
                keyboard_page.append(
                    InlineKeyboardButton(
                        self.current_page_label.format(page) if self._page == page else str(page),
                        callback_data=self._page_callback.set_data(page=page))
                )
        else:
            keyboard_page = self._build_multi_pages()
        keyboard_data = self._build_data()
        self._keyboard = build_menu(keyboard_data, footer_buttons=keyboard_page)

    def _build_data(self):
        keyboard = []
        for value in self.data:
            keyboard.append(
                InlineKeyboardButton(
                    self._title_pattern.format(**value),
                    callback_data=self._callback.set_data(
                        **{key: value for key, value in value.items() if key in self._callback_data_keys}
                    )
                )
            )
        return keyboard

    def _build_multi_pages(self):
        if self._page <= 3:
            return self._build_start_keyboard()
        elif self._page > self.page_count - 3:
            return self._build_finish_keyboard()
        else:
            return self._build_middle_keyboard()

    def _build_start_keyboard(self):
        keyboard_list = []
        count = 4
        for page in range(1, count):
            keyboard_list.append(
                InlineKeyboardButton(
                    self.current_page_label.format(page) if self._page == page else str(page),
                    callback_data=self._page_callback.set_data(page=page)
                )
            )
        keyboard_list.extend([
            InlineKeyboardButton(
                self.next_page_label.format(count),
                callback_data=self._page_callback.set_data(page=count)),
            InlineKeyboardButton(
                str(self.page_count),
                callback_data=self._page_callback.set_data(page=self.page_count))
        ])
        return keyboard_list

    def _build_finish_keyboard(self):
        keyboard_list = []
        keyboard_list.extend([
            InlineKeyboardButton(self.first_page_label.format(1), callback_data=self._page_callback.set_data(page=1)),
            InlineKeyboardButton(
                self.previous_page_label.format(self.page_count - 3),
                callback_data=self._page_callback.set_data(page=self.page_count - 3)
            )
        ])
        for page in range(self.page_count - 2, self.page_count + 1):
            keyboard_list.append(
                InlineKeyboardButton(
                    self.current_page_label.format(page) if self._page == page else str(page),
                    callback_data=self._page_callback.set_data(page=page)
                )
            )
        return keyboard_list

    def _build_middle_keyboard(self):
        return [
            InlineKeyboardButton(
                self.first_page_label.format(1),
                callback_data=self._page_callback.set_data(page=1)
            ),
            InlineKeyboardButton(
                self.previous_page_label.format(self._page - 1),
                callback_data=self._page_callback.set_data(page=self._page - 1)
            ),
            InlineKeyboardButton(
                self.current_page_label.format(self._page),
                callback_data=self._page_callback.set_data(page=self._page)),
            InlineKeyboardButton(
                self.next_page_label.format(self._page + 1),
                callback_data=self._page_callback.set_data(page=self._page + 1)
            ),
            InlineKeyboardButton(
                self.last_page_label.format(self.page_count),
                callback_data=self._page_callback.set_data(page=self.page_count)
            )
        ]

    @property
    def inline_markup(self):
        if self._keyboard is None:
            self._build()
        return InlineKeyboardMarkup(self._keyboard)
