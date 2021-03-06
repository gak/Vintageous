import sublime
import os

import itertools


REG_UNNAMED = '"'
REG_SMALL_DELETE = '-'
REG_BLACK_HOLE = '_'
REG_LAST_INSERTED_TEXT = '.'
REG_FILE_NAME = '%'
REG_ALT_FILE_NAME = '#'
REG_SYS_CLIPBOARD_1 = '*'
REG_SYS_CLIPBOARD_2 = '+'
REG_SYS_CLIPBOARD_ALL = (REG_SYS_CLIPBOARD_1, REG_SYS_CLIPBOARD_2)
REG_ALL = (REG_UNNAMED, REG_SMALL_DELETE, REG_BLACK_HOLE,
           REG_LAST_INSERTED_TEXT, REG_FILE_NAME, REG_ALT_FILE_NAME,
           REG_SYS_CLIPBOARD_1, REG_SYS_CLIPBOARD_2)
# todo(guillermo): There are more.


# Registers must be available globally, so store here the data.
_REGISTER_DATA = {}


# todo(guillermooo): Subclass dict properly.
class Registers(object):
    """
    Registers hold global data mainly used by yank, delete and paste.

    This class is meant to be used a descriptor.

        class VintageState(object):
            ...
            self.registers = Registers()

        vstate = VintageState()
        vstate.registers["%"] # now vstate.registers has access to the
                              # current view.

    And this is how you access registers:

    Setting registers...

        vstate.registers['a'] = "foo" # => a == "foo"
        vstate.registers['A'] = "bar" # => a == "foobar"
        vstate.registers['1'] = "baz" # => 1 == "baz"
        vstate.registers[1] = "fizz"  # => 1 == "fizz"

    Retrieving registers...

        vstate.registers['a'] # => "foobar"
        vstate.registers['A'] # => "foobar" (synonyms)
    """


    def __init__(self, view=None, settings=None):
        self.view = view
        self.settings = settings

    def __get__(self, instance, owner):
        # This ensures that we can easiy access the active view.
        return Registers(instance.view, instance.settings)

    def _set_default_register(self, value):
        # todo(guillermo): could be made a decorator.
        _REGISTER_DATA[REG_UNNAMED] = value

    def _maybe_set_sys_clipboard(self, name, value):
        # We actually need to check whether the option is set to a bool; could
        # be any JSON type.
        if (name == REG_SYS_CLIPBOARD_1 or
            self.settings.view['vintageous_use_sys_clipboard'] == True):
                # Make sure Sublime Text does the right thing in the presence of multiple
                # selections.
                if len(value) > 1:
                    self.view.run_command('copy')
                else:
                    sublime.set_clipboard(value[0])

    def set(self, name, value):
        """
        Sets an a-z or 0-9 register.
        """
        # We accept integers as register names.
        name = str(name)
        assert len(str(name)) == 1, "Register names must be 1 char long."

        if name == REG_BLACK_HOLE:
            return

        # Special registers and invalid registers won't be set.
        if (not (name.isalpha() or name.isdigit() or
                 name.isupper() or name == REG_UNNAMED or
                 name == REG_SYS_CLIPBOARD_1)):
                    # Vim fails silently.
                    # raise Exception("Can only set a-z and 0-9 registers.")
                    return None
        _REGISTER_DATA[name] = value
        self._set_default_register(value)
        self._maybe_set_sys_clipboard(name, value)

    def append_to(self, name, value):
        """
        Appends to an a-z register. `name` must be a capital in A-Z.
        """
        assert len(name) == 1, "Register names must be 1 char long."
        assert ord(name) in range(ord('A'), ord('Z') + 1), "Can only append to A-Z registers."

        existing_values = _REGISTER_DATA.get(name.lower(), '')
        new_values = itertools.zip_longest(existing_values, value, fillvalue='')
        new_values = [(prefix + suffix) for (prefix, suffix) in new_values]
        _REGISTER_DATA[name.lower()] = new_values
        self._set_default_register(new_values)
        self._maybe_set_sys_clipboard(name, new_values)

    def get(self, name=REG_UNNAMED):
        # We accept integers or strings a register names.
        name = str(name)
        assert len(str(name)) == 1, "Register names must be 1 char long."

        # Did we request a special register?
        if name == REG_BLACK_HOLE:
            return
        elif name == REG_FILE_NAME:
            try:
                return os.path.basename(self.view.file_name())
            except AttributeError:
                return ''
        elif name in REG_SYS_CLIPBOARD_ALL:
            return [sublime.get_clipboard()]
        elif name != REG_UNNAMED and name in REG_ALL:
            return
        # Special case lumped among these --user always wants the sys
        # clipboard.
        elif name == REG_UNNAMED and self.settings.view['vintageous_use_sys_clipboard'] == True:
            return sublime.get_clipboard()

        # We requested an [a-z0-9"] register.
        try:
            # In Vim, "A and "a seem to be synonyms, so accept either.
            return _REGISTER_DATA[name.lower()]
        except KeyError:
            # sublime.status_message("Vintage.Next: E353 Nothing in register %s", name)
            pass

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        try:
            if key.isupper():
                self.append_to(key, value)
            else:
                self.set(key, value)
        except AttributeError:
            self.set(key, value)
