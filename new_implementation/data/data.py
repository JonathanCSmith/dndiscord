import os
import json
from collections import OrderedDict

from discord import Role


class PermissionData:
    def __init__(self, minimum_execute_level=-1, allowed_roles=None):
        self.minimum_execute_level = minimum_execute_level

        if allowed_roles is None:
            allowed_roles = set()
        self.allowed_roles = allowed_roles

    def get_minimum_execution_level(self):
        return self.minimum_execute_level

    def set_minimum_execution_level(self, minimum_execute_level):
        self.minimum_execute_level = minimum_execute_level

    def get_allowed_roles(self):
        return self.allowed_roles

    def add_allowed_role(self, role: Role):
        self.allowed_roles.append(role.name)

    def remove_allowed_role(self, role: Role):
        self.allowed_roles.remove(role.name)


class PermissionHolder:
    def __init__(self, permissions=None, default_permissions=None):
        if permissions is None:
            permissions = dict()
        self.permissions = permissions

        if default_permissions is None:
            default_permissions = dict()
        self.default_permissions = default_permissions

    def get_permissions_for(self, id):
        if id in self.permissions:
            return self.permissions[id]

        return PermissionData()

    def get_default_permissions_for(self, id):
        if id in self.permissions:
            return self.permissions[id]

        return PermissionData()


class ModuleDataHolder:
    def __init__(self, module_data=None):
        if module_data is None:
            module_data = dict()
        self.module_data = module_data

    def get_module_data(self, key):
        if key in self.module_data:
            return self.module_data[key]
        return None

    def set_module_data(self, key, module_data):
        self.module_data[key] = module_data


class SerializationModifier:
    def __init__(self):
        self.ignored_items = list()

    def add_item_to_be_ignored(self, item):
        self.ignored_items.append(item)

    def get_dict_items_that_should_not_be_serialized(self):
        return self.ignored_items


class ContextDependent(SerializationModifier):
    def __init__(self):
        super().__init__()
        self.current_path = None
        self.add_item_to_be_ignored("current_path")

    def set_file_location(self, path):
        self.current_path = path


def convert_to_dict(obj):
    """
    A function takes in a custom object and returns a dictionary representation of the object.
    This dict representation includes meta data such as the object's module and class names.
    """

    #  Populate the dictionary with object meta data
    obj_dict = OrderedDict()
    obj_dict.update({
        "__class__": obj.__class__.__name__,
        "__module__": obj.__module__
    })

    #  Populate the dictionary with object properties
    obj_dict.update(obj.__dict__)

    # Do not serialize out anything we shouldn't
    if isinstance(obj, SerializationModifier):
        ignored_items = obj.get_dict_items_that_should_not_be_serialized()

        # Loop through any provided items to remove them
        for ignored_item in ignored_items:
            del obj_dict[ignored_item]

    return obj_dict


def dict_to_obj(our_dict):
    """
    Function that takes in a dict and returns a custom object associated with the dict.
    This function makes use of the "__module__" and "__class__" metadata in the dictionary
    to know which object type to create.
    """
    if "__class__" in our_dict:
        # Pop ensures we remove metadata from the dict to leave only the instance arguments
        class_name = our_dict.pop("__class__")

        # Get the module name from the dict and import it
        module_name = our_dict.pop("__module__")

        # We use the built in __import__ function since the module name is not yet known at runtime
        components = module_name.split(".")
        module = __import__(components[0])
        for comp in components[1:]:
            module = getattr(module, comp)

        # Get the class from the module
        class_ = getattr(module, class_name)

        # Use dictionary unpacking to initialize the object
        obj = class_(**our_dict)
    else:
        obj = our_dict
    return obj


class DataAccessObject:
    def __init__(self):
        self.payload = None
        self.path = ""

    def get_payload(self):
        return self.payload

    def set_payload(self, obj):
        self.payload = obj

    async def load(self, path):
        self.path = path
        self.payload = load(self.path)

    async def save(self, path):
        self.path = path
        save(self.payload, self.path)


def save(obj, file):
    directory = os.path.dirname(file)
    if not os.path.exists(directory):
        os.makedirs(directory)
    data = json.dumps(obj, default=convert_to_dict, indent=4)
    with open(file, "w") as json_file:
        json_file.write(data)


def load(file):
    if not os.path.isfile(file):
        return None

    with open(file, "r") as json_file:
        obj = json.load(json_file, object_hook=dict_to_obj)
        if isinstance(obj, ContextDependent):
            obj.set_file_location(os.path.dirname(file))

        return obj
