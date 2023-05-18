import re
import sys
import time
import threading
from typing import Callable
import keyboard
import ctypes
from ctypes import wintypes


class Flag:
    input_marker = 1
    general = 3


class Bag:
    def __init__(self, cli):
        self.__cli = cli
        self.__values = {}

    def __getitem__(self, key):
        return self.__values[key]

    def __setitem__(self, key, value):
        self.__values[key] = value

    def print(self, text, end=None):
        self.__cli.print(text, end)


class Window:
    def __init__(self):
        self.__user32 = ctypes.windll.user32
        pid = wintypes.DWORD()
        self.__user32.GetWindowThreadProcessId(self.__user32.GetForegroundWindow(), ctypes.byref(pid))
        self.__id = pid.value

    def is_focused(self):
        pid = wintypes.DWORD()
        self.__user32.GetWindowThreadProcessId(self.__user32.GetForegroundWindow(), ctypes.byref(pid))
        return pid.value == self.__id


class Command:
    def __init__(self, cmd, target, group, args, wait):
        self.command = cmd
        self.target = target
        self.group = group
        self.arguments = args
        self.wait = wait


class Keybind:
    def __init__(self, keys, target):
        self.keys = keys
        self.target = target


class Cli:
    def __init__(self):
        self.window = Window()

        self.__stop_flag = False
        self.__pause_flag = True
        self.__console_flag = False

        self.__marker = '>'
        self.__actions: list[Command] = []
        self.__dict_of_actions_by_groupcommand = {}
        self.__dict_of_commands_by_group = {'main': []}

        self.__dict_of_keybinds = {}

        self.__to_print = []

        self.__bag = Bag(self)

    def config(self, allow_console: bool = True, start_on_console: bool = False, prompt: str = None):
        self.__console_flag = start_on_console
        self.__marker = prompt if prompt is not None else self.__marker

    def run(self):
        threading.Thread(target=self.__thread_key_press_monitor, daemon=True).start()
        threading.Thread(target=self.__thread_console_command_monitor, daemon=True).start()
        threading.Thread(target=self.__thread_serial_print, daemon=True).start()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                quit()

    def add_command(self, command: str, target: Callable, group: str = None, args=None, wait: bool = True,
                    run_on_startup: bool = False):
        group = 'main' if group is None else group.lower()
        command = command.lower()
        args = (args,) if type(args) not in [tuple, type(None)] else args
        wait = wait if not run_on_startup else False

        if group in self.__dict_of_commands_by_group:
            if command in self.__dict_of_commands_by_group[group]:
                raise Exception

        if args is not None and not run_on_startup:
            raise Exception

        if not re.fullmatch(r'_+', command):
            action = Command(command, target, group, args, wait)
            self.__dict_of_actions_by_groupcommand[group + command] = action
            if group not in self.__dict_of_commands_by_group:
                self.__dict_of_commands_by_group[group] = []
            self.__dict_of_commands_by_group[group].append(command)

        if run_on_startup:
            user_input_args = list(args) if args is not None else []
            for i, arg in enumerate(target.__code__.co_varnames):
                if arg.lower() == 'bag':
                    user_input_args.insert(i, self.__bag)
            if len(user_input_args) > 0:
                threading.Thread(target=target, args=tuple(user_input_args)).start()
            else:
                threading.Thread(target=target).start()

    def add_keybind(self, keybind: str, target: Callable):
        keybind = keybind.lower()
        if not re.fullmatch(r'[A-z0-9]+(\+[A-z0-9]*)*', keybind):
            raise Exception
        if keybind in self.__dict_of_keybinds:
            raise Exception
        if keybind == 'ctrl+c':
            raise Exception
        self.__dict_of_keybinds[keybind] = Keybind(keybind, target)

    def __print(self, text=None, end=None, flag=Flag.general):
        if not self.__console_flag:
            print(text)
        elif flag == Flag.general:
            self.__to_print.append({'value': text, 'end': end})
        elif flag == Flag.input_marker:
            print('\b\b\b'+self.__marker, end='')

    def print(self, text, end=None):
        self.__print(text, end, flag=Flag.general)

    def __thread_key_press_monitor(self):
        def key_released(key: str):
            released = False

            def set_released(value: bool):
                nonlocal released
                released = value

            keyboard.on_release_key(key, lambda _: set_released(True))

            return released
        enter_pressed = 0
        while not self.__stop_flag:
            if self.__console_flag:
                enter_pressed = 0

            if self.window.is_focused():
                if keyboard.is_pressed('ctrl+c'):
                    self.__console_flag = not self.__console_flag
                    if self.__console_flag:
                        self.__print(flag=Flag.input_marker)
                    else:
                        print()

                while not key_released('c') and keyboard.is_pressed('c'):
                    time.sleep(0.05)

                if keyboard.is_pressed('enter'):
                    enter_pressed += 1
                    if not self.__console_flag:
                        if enter_pressed >= 2:
                            _ = input()
                while not key_released('enter') and keyboard.is_pressed('enter'):
                    time.sleep(0.05)

                for keybind in self.__dict_of_keybinds.values():
                    last_key = keybind.keys.split('+')[-1]
                    if keyboard.is_pressed(keybind.keys):
                        args = keybind.target.__code__.co_varnames
                        if len(args) == 1 and args[0].lower() == 'bag':
                            threading.Thread(target=keybind.target, args=(self.__bag,), daemon=True).start()
                        else:
                            threading.Thread(target=keybind.target, daemon=True).start()
                    while not key_released(last_key) and keyboard.is_pressed(last_key):
                        time.sleep(0.05)

            time.sleep(0.05)

    def __thread_console_command_monitor(self):
        while not self.__stop_flag:
            if self.__console_flag:
                self.__print(flag=Flag.input_marker)
                user_input = input()
                if not self.__console_flag:
                    user_input = ''
                user_input_args = [x.replace('"', '') for x in re.findall(r'(\"[^\"]*\")', user_input)]
                user_input = re.sub(r'(\"[^\"]*\")', '{var}', user_input).split(' ')

                if len(user_input) < 2:
                    group = 'main'
                    cmd = user_input.pop(0)
                elif user_input[0] not in self.__dict_of_commands_by_group:
                    group = 'main'
                    cmd = user_input.pop(0)
                else:
                    group = user_input.pop(0)
                    cmd = user_input.pop(0)

                aux = user_input_args
                user_input_args = [aux.pop(0) if x == '{var}' else x for x in user_input]

                if group is None or cmd is None:
                    raise Exception

                if cmd in self.__dict_of_commands_by_group[group]:
                    action = self.__dict_of_actions_by_groupcommand[group + cmd]
                    for i, arg in enumerate(action.target.__code__.co_varnames):
                        if arg.lower() == 'bag':
                            user_input_args.insert(i, self.__bag)
                    if user_input_args:
                        thread = threading.Thread(target=action.target, args=tuple(user_input_args), daemon=True)
                    else:
                        thread = threading.Thread(target=action.target, daemon=True)
                    if action.wait:
                        self.__console_flag = False
                        thread.start()
                        while thread.is_alive():
                            time.sleep(0.1)
                    else:
                        thread.start()
                    self.__console_flag = True
            time.sleep(0.1)

    def __thread_serial_print(self):
        while not self.__stop_flag:
            if self.__to_print:
                if not self.__console_flag:
                    content = self.__to_print.pop(0)
                    print(str(content['value']), end=content['end'] if content['end'] is not None else '\n')
            time.sleep(0.05)