from new_implementation.core.permissions_handler import PermissionsHandler
from new_implementation.core.resource_handler import ResourceHandler


class Engine:
    def __init__(self, engine_name):
        self.engine_name = engine_name
        self.memory_mutex = False  # Definitely not threadsafe?
        self.listeners = dict()

        self.resource_handler = ResourceHandler(self)
        self.permissions_handler = PermissionsHandler(self)

    def get_engine_name(self):
        return self.engine_name

    def get_resource_handler(self):
        return self.resource_handler

    def get_permission_handler(self):
        return self.permissions_handler

    def register_event_class(self, clazz):
        if clazz not in self.listeners:
            self.listeners[clazz] = list()

    def register_event_class_listener(self, clazz, listener):
        if clazz not in self.listeners:
            return False

        self.listeners[clazz].append(listener)

    def get_event_class_listeners(self, clazz):
        return self.listeners[clazz]

    def is_memory_mutex_locked(self):
        return self.memory_mutex

    async def purge_memory(self):
        self.memory_mutex = True
        self.memory_mutex = False


