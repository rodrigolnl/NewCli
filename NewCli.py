import re
import time
import threading
from typing import Callable
import keyboard
import ctypes
from ctypes import wintypes


class Bag:
    def __init__(self, cli):
        self.__cli: Cli = cli
        self.__values = {}

    def __getitem__(self, key):
        if key in self.__values:
            return self.__values[key]
        else:
            self.__values[key] = None
            return self.__values[key]

    def __setitem__(self, key, value):
        self.__values[key] = value

    def print(self, text='', end=None):
        self.__cli.print(text, end)

    def input(self):
        return self.__cli.input()

    def set_interactive(self):
        self.__cli.force_interactive()

    def set_non_interactive(self):
        self.__cli.force_non_interactive()


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
    def __init__(self, keys, target, args=None):
        self.keys = keys
        self.target = target
        self.args: tuple | None = args


class Service:
    def __init__(self, target, args):
        self.target = target
        self.arguments = args


class Cli:
    Bag = Bag

    def __init__(self):
        self.window = Window()

        self.__actions: list[Command] = []
        self.__dict_of_actions_by_groupcommand: dict[str, Command] = {}
        self.__dict_of_commands_by_group: dict[str, list[str]] = {'main': []}
        self.__list_of_actions_on_startup: list[Service] = []
        self.__dict_of_keybinds: dict[str, Keybind] = {}

        self.__to_print = []
        self.__bag = Bag(self)
        self.__stop_flag = False
        self.__pause_flag = True

        self.not_found_msg = 'Command not found!'
        self.__marker = '>'
        self.__show_info = True

        # mode: [ interactive | non-interactive ]
        self.__mode = 'non-interactive'

    def config(self, allow_interactive: bool = True, start_on_interactive: bool = None, prompt: str = None,
               not_found_msg: str = None, show_info: bool = None):
        self.__marker = prompt if prompt is not None else self.__marker
        self.__mode = 'interactive' if start_on_interactive else 'non-interactive'
        self.not_found_msg = not_found_msg if not_found_msg is not None else self.not_found_msg
        self.__show_info = show_info if show_info is not None else self.__show_info

    def run(self):
        if self.__show_info:
            print('Press "ctrl+i" to alternate between interactive and non-interactive mode!')

        for action in self.__list_of_actions_on_startup:
            execution_args = list(action.arguments) if action.arguments is not None else []
            for i, arg in enumerate(action.target.__code__.co_varnames):
                if arg.lower() == 'bag':
                    execution_args.insert(i, self.__bag)
            if len(execution_args) > 0:
                threading.Thread(target=action.target, args=tuple(execution_args), daemon=True).start()
            else:
                threading.Thread(target=action.target, daemon=True).start()

        threading.Thread(target=self.__thread_key_press_monitor, daemon=True).start()
        threading.Thread(target=self.__thread_console_command_monitor, daemon=True).start()
        threading.Thread(target=self.__thread_serial_print, daemon=True).start()

        while not self.__stop_flag:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                self.__stop_flag = True
                quit()

    def add_command(self, command: str, target: Callable, group: str = None, synchronous: bool = True):
        group = 'main' if group is None else group.lower()
        command = command.lower()

        if group in self.__dict_of_commands_by_group:
            if command in self.__dict_of_commands_by_group[group]:
                raise Exception(f'"{group + " " if group != "main" else ""}{command}" already in use.')

        action = Command(command, target, group, tuple(), synchronous)
        self.__dict_of_actions_by_groupcommand[group + command] = action
        if group not in self.__dict_of_commands_by_group:
            self.__dict_of_commands_by_group[group] = []
        self.__dict_of_commands_by_group[group].append(command)

    def add_keybind(self, keybind: str, target: Callable, args=None):
        args = (args,) if args is not None and type(args) is not tuple else args
        keybind = keybind.lower()
        if not re.fullmatch(r'[A-z0-9]+(\+[A-z0-9]*)*', keybind):
            raise Exception('This is not a valid keybind string. The expected format is "{key}" or {key}+{key}')
        if keybind in self.__dict_of_keybinds:
            raise Exception(f'{keybind} already in use.')
        if keybind == 'ctrl+i':
            raise Exception('ctrl+i is a reserved keybind to alter between the interactive mode. It can not be changed.')
        self.__dict_of_keybinds[keybind] = Keybind(keybind, target, args)

    def add_service(self, target: Callable, args=None):
        args = (args,) if type(args) not in [tuple, type(None)] else args
        self.__list_of_actions_on_startup.append(Service(target, args))

    def print(self, text, end=None):
        self.__to_print.append({'value': text, 'end': end})

    def input(self):
        self.__mode = 'non-interactive'
        user_input = input()
        self.__mode = 'interactive'
        return user_input

    def force_interactive(self):
        self.__mode = 'interactive'
        print(self.__marker, end='')

    def force_non_interactive(self):
        self.__mode = 'non-interactive'

    def quit(self):
        self.__stop_flag = True
        quit()

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
            if self.__mode == 'interactive':
                enter_pressed = 0

            if self.window.is_focused():

                if keyboard.is_pressed('ctrl+i'):
                    self.__mode = 'interactive' if self.__mode == 'non-interactive' else 'non-interactive'
                    if self.__mode == 'interactive':
                        print(self.__marker, end='')
                    else:
                        print()
                while not key_released('i') and keyboard.is_pressed('i'):
                    time.sleep(0.05)

                if keyboard.is_pressed('enter'):
                    enter_pressed += 1
                    if not self.__mode == 'interactive':
                        if enter_pressed >= 2:
                            _ = input()
                while not key_released('enter') and keyboard.is_pressed('enter'):
                    time.sleep(0.05)

                for keybind in self.__dict_of_keybinds.values():
                    last_key = keybind.keys.split('+')[-1]
                    if keyboard.is_pressed(keybind.keys):
                        args = keybind.target.__code__.co_varnames
                        self.__mode = 'non-interactive'
                        if len(args) >= 1 and args[0].lower() == 'bag':
                            execution_args = ()
                            declaration_args = list(keybind.args)
                            for arg in args:
                                if arg.lower() == 'bag':
                                    execution_args += (self.__bag,)
                                else:
                                    execution_args += (declaration_args.pop(0),)

                            thread = threading.Thread(target=keybind.target, args=execution_args, daemon=True)
                        else:
                            thread = threading.Thread(target=keybind.target, daemon=True)
                        thread.start()
                    while not key_released(last_key) and keyboard.is_pressed(last_key):
                        time.sleep(0.05)

            time.sleep(0.05)

    def __thread_console_command_monitor(self):
        try:
            while not self.__stop_flag:
                if self.__mode == 'interactive':
                    print(f'\b{self.__marker}', end='')
                    user_input = input()
                    if self.__mode != 'interactive':
                        user_input = ''
                        continue
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
                        self.__mode = 'non-interactive'
                        thread.start()
                        if action.wait:
                            while thread.is_alive():
                                time.sleep(0.1)
                        self.__mode = 'interactive'
                    else:
                        print(self.not_found_msg, end='' if self.not_found_msg == '' else '\n')
                time.sleep(0.1)
        except Exception:
            pass

    def __thread_serial_print(self):
        while not self.__stop_flag:
            if self.__to_print:
                if self.__mode == 'non-interactive':
                    content = self.__to_print.pop(0)
                    print(str(content['value']), end=content['end'] if content['end'] is not None else '\n')
            time.sleep(0.05)
