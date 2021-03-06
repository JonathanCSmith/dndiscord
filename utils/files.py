import json
import os
from collections import OrderedDict


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


def save(obj, file):
    data = json.dumps(obj, default=convert_to_dict, indent=4)
    with open(file, "w") as json_file:
        json_file.write(data)


def load(file):
    with open(file, "r") as json_file:
        obj = json.load(json_file, object_hook=dict_to_obj)
        if isinstance(obj, ContextDependent):
            obj.set_file_location(os.path.dirname(file))

    return obj
