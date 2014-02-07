"""This module contains functions and classes for creating and issuing events.

    .. attribute:: keys

        A special attribute for accessing the constants associated with a given
        key. For instance, `spyral.keys.down` and `spyral.keys.f`. This is
        useful for testing for keyboard events. A complete list of all the key
        constants can be found in the appendix.

    .. attribute:: mods

        A special attribute for accessing the constants associated with a given
        mod key. For instance, `spyral.mods.lshift` (left shift) and
        `spyral.mods.ralt` (Right alt). This is useful for testing for keyboard
        events. A complete list of all the key constants can be found in the
        appendix.

"""

import pygame
try:
    import json
except ImportError:
    import simplejson as json
import spyral
import os
import random
import base64

_TYPE_TO_ATTRS = None
_TYPE_TO_TYPE = None

class Event(object):
    """
    A simple representation of an event. Keyword arguments will be named
    attributes of the Event::

        collision_event = Event(ball=ball, paddle=paddle)
        spyral.event.queue("ball.collides.paddle", collision_event)
    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

# This might actually be unused!
_EVENT_NAMES = ['QUIT', 'ACTIVEEVENT', 'KEYDOWN', 'KEYUP', 'MOUSEMOTION',
                'MOUSEBUTTONUP', 'VIDEORESIZE', 'VIDEOEXPOSE', 'USEREVENT',
                'MOUSEBUTTONDOWN']

def _init():
    """
    Initializes the Event system, which requires mapping the Pygame event
    constants to Spyral strings.
    """
    global _TYPE_TO_ATTRS
    global _TYPE_TO_TYPE

    _TYPE_TO_ATTRS = {
        pygame.QUIT: tuple(),
        pygame.ACTIVEEVENT: ('gain', 'state'),
        pygame.KEYDOWN: ('unicode', 'key', 'mod'),
        pygame.KEYUP: ('key', 'mod'),
        pygame.MOUSEMOTION: ('pos', 'rel', 'buttons'),
        pygame.MOUSEBUTTONUP: ('pos', 'button'),
        pygame.MOUSEBUTTONDOWN: ('pos', 'button'),
        pygame.VIDEORESIZE: ('size', 'w', 'h'),
        pygame.VIDEOEXPOSE: ('none'),
    }
    _TYPE_TO_TYPE = {
        pygame.QUIT: "system.quit",
        pygame.ACTIVEEVENT: "system.focus_change",
        pygame.KEYDOWN: "input.keyboard.down",
        pygame.KEYUP: "input.keyboard.up",
        pygame.MOUSEMOTION: "input.mouse.motion",
        pygame.MOUSEBUTTONUP: "input.mouse.up",
        pygame.MOUSEBUTTONDOWN: "input.mouse.down",
        pygame.VIDEORESIZE: "system.video_resize",
        pygame.VIDEOEXPOSE: "system.video_expose",
    }

def queue(event_name, event=None, _scene=None):
    """
    Queues a new event in the system, meaning that it will be run at the next
    available opportunity.

    :param str event_name: The type of event (e.g., "system.quit",
                           "input.mouse.up", or "pong.score".
    :param event: An Event object that holds properties for the event.
    :type event: :class:`Event <spyral.event.Event>`
    :param _scene: The scene to queue this event on; if `None` is given, the
                   currently executing scene will be used.
    :type _scene: :class:`Scene <spyral.Scene>` or `None`.
    """
    if _scene is None:
        _scene = spyral._get_executing_scene()
    _scene._queue_event(event_name, event)

def handle(event_name, event=None, _scene=None):
    """
    Instructs spyral to execute the handlers for this event right now. When you
    have a custom event, this is the function you call to have the event occur.

    :param str event_name: The type of event (e.g., "system.quit",
                           "input.mouse.up", or "pong.score".
    :param event: An Event object that holds properties for the event.
    :type event: :class:`Event <spyral.event.Event>`
    :param _scene: The scene to queue this event on; if `None` is given, the
                   currently executing scene will be used.
    :type _scene: :class:`Scene <spyral.Scene>` or `None`.
    """
    if _scene is None:
        _scene = spyral._get_executing_scene()
    _scene._handle_event(event_name, event)

def _pygame_to_spyral(event):
    """
    Convert a Pygame event to a Spyral event, correctly converting arguments to
    attributes.
    """
    event_attrs = _TYPE_TO_ATTRS[event.type]
    event_type = _TYPE_TO_TYPE[event.type]
    e = Event()
    for attr in event_attrs:
        setattr(e, attr, getattr(event, attr))
    if event_type.startswith("input"):
        setattr(e, "type", event_type.split(".")[-1])
    if event_type.startswith('input.keyboard'):
        k = keys.reverse_map.get(event.key, 'unknown')
        event_type += '.' + k

    return (event_type, e)

class EventHandler(object):
    """
    Base event handler class.
    """
    def __init__(self):
        self._events = []
        self._mouse_pos = (0, 0)

    def tick(self):
        """
        Should be called at the beginning of update cycle. For the
        event handler which is part of a scene, this function will be
        called automatically. For any additional event handlers, you
        must call this function manually.
        """
        pass

    def get(self, types=[]):
        """
        Gets events from the event handler. Types is an optional
        iterable which has types which you would like to get.
        """
        try:
            types[0]
        except IndexError:
            pass
        except TypeError:
            types = (types,)

        if types == []:
            ret = self._events
            self._events = []
            return ret

        ret = [e for e in self._events if e['type'] in types]
        self._events = [e for e in self._events if e['type'] not in types]
        return ret


class LiveEventHandler(EventHandler):
    """
    An event handler which pulls events from the operating system.

    The optional output_file argument specifies the path to a file
    where the event handler will save a custom json file that can
    be used with the `ReplayEventHandler` to show replays of a
    game in action, or be used for other clever purposes.

    .. note::

        If you use the output_file parameter, this function will
        reseed the random number generator, save the seed used. It
        will then be restored by the ReplayEventHandler.
    """
    def __init__(self, output_file=None):
        EventHandler.__init__(self)
        self._save = output_file is not None
        if self._save:
            self._file = open(output_file, 'w')
            seed = os.urandom(4)
            info = {'random_seed': base64.encodestring(seed)}
            random.seed(seed)
            self._file.write(json.dumps(info) + "\n")

    def tick(self):
        mouse = pygame.mouse.get_pos()
        events = pygame.event.get()
        self._mouse_pos = mouse
        self._events.extend(events)
        # if self._save:
        #     d = {'mouse': mouse, 'events': events}
        #     self._file.write(json.dumps(d) + "\n")

    def __del__(self):
        if self._save:
            self._file.close()


class ReplayEventHandler(EventHandler):
    """
    An event handler which replays the events from a custom json
    file saved by the `LiveEventHandler`.
    """
    def __init__(self, input_file):
        EventHandler.__init__(self)
        self._file = open(input_file)
        info = json.loads(self._file.readline())
        random.seed(base64.decodestring(info['random_seed']))
        self.paused = False

    def pause(self):
        """
        Pauses the replay of the events, making tick() a noop until
        resume is called.
        """
        self.paused = True

    def resume(self):
        """
        Resumes the replay of events.
        """
        self.paused = False

    def tick(self):
        if self.paused:
            return
        try:
            d = json.loads(self._file.readline())
        except ValueError:
            spyral.director.pop()
        events = d['events']
        events = [EventDict(e) for e in events]
        self._mouse_pos = d['mouse']
        self._events.extend(events)

class Mods(object):
    def __init__(self):
        self.none = pygame.KMOD_NONE
        self.lshift = pygame.KMOD_LSHIFT
        self.rshift = pygame.KMOD_RSHIFT
        self.shift = pygame.KMOD_SHIFT
        self.caps = pygame.KMOD_CAPS
        self.ctrl = pygame.KMOD_CTRL
        self.lctrl = pygame.KMOD_LCTRL
        self.rctrl = pygame.KMOD_RCTRL
        self.lalt = pygame.KMOD_LALT
        self.ralt = pygame.KMOD_RALT
        self.alt = pygame.KMOD_ALT

class Keys(object):

    def __init__(self):
        self.reverse_map = {}
        self.load_keys_from_file(spyral._get_spyral_path() +
                                 'resources/default_key_mappings.txt')

    def load_keys_from_file(self, filename):
        fp = open(filename)
        key_maps = fp.readlines()
        fp.close()
        for single_mapping in key_maps:
            mapping = single_mapping[:-1].split(' ')
            if len(mapping) == 2:
                if mapping[1][0:2] == '0x':
                    setattr(self, mapping[0], int(mapping[1], 16))
                    self.reverse_map[int(mapping[1], 16)] = mapping[0]
                else:
                    setattr(self, mapping[0], int(mapping[1]))
                    self.reverse_map[int(mapping[1])] = mapping[0]

    def add_key_mapping(self, name, number):
        setattr(self, name, number)

keys = Keys()
mods = Mods()
