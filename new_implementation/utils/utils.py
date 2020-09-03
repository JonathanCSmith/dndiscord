import importlib
import inspect


def get_guild_id_from_context(context):
    return str(context.guild.id)


def get_user_id_from_context(context):
    return str(context.author.id)


def load_class(path, interface):
    module = importlib.import_module(path)
    results = list()

    # Inspect every class to see if it implements the provided interface
    for name, cls in inspect.getmembers(module, inspect.isclass):
        if isinstance(cls, interface):
            results.append(cls)

    # Handle non singleton results
    if len(results) > 1:
        print("Too many classes were available in the file provided at: " + path + " and therefore the class to load could not be identified")
    elif len(results) == 0:
        print("No classes were found implementing the " + interface.__name__ + " inside the file: " + path)
    else:
        return results[0]
