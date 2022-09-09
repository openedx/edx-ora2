from inspect import isclass
from pkgutil import iter_modules
from pathlib import Path
from importlib import import_module

from ..interface import CodeExecutor


# Load all modules when `executors` is loaded. This allows reflection to discover subclasses.
#
# iterate through the modules in the current package
package_dir = Path(__file__).resolve().parent
for (_, module_name, _) in iter_modules([str(package_dir)]):

    # import the module and iterate through its attributes
    module = import_module('{}.{}'.format(__name__, module_name))
    for attribute_name in dir(module):
        attribute = getattr(module, attribute_name)

        if isclass(attribute) and issubclass(attribute, CodeExecutor):
            # Add the class to this package's variables
            globals()[attribute_name] = attribute
