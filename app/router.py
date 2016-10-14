# router.py -- adds routing to Flask app

import os
import sys

import re
import importlib
import inflect

import flask_classy as fc

_fc_get_interesting_members = fc.get_interesting_members

class Router(object):
  def get_controllers_path(self, args):
    controllers_path = None

    controllers_path = controllers_path or args["views_path"] if "views_path" in args else None
    controllers_path = controllers_path or args["controllers_path"] if "controllers_path" in args else None
    
    if controllers_path and os.path.exists(controllers_path):
      return controllers_path 

    controller_directories = [os.path.dirname(__file__) + "/" + tag for tag in ["views", "controllers"]]

    for directory in controller_directories:
      if os.path.exists(directory):
        return directory

    raise Exception, "No controller directories found."

  def get_controller_class_name(self, controller_module_name):
    separator_pos = controller_module_name.index("_")

    return controller_module_name[0:separator_pos].capitalize() + controller_module_name[separator_pos:].capitalize()

  def get_controller_module_name(self, controller_file_name):
    return os.path.splitext(controller_file_name)[0]

  def get_model_module_name(self, model_file_name):
    return os.path.splitext(model_file_name)[0]

  def get_model_class_name(self, model_module_name):
    return model_module_name.lower().capitalize()

  def get_models_path(self, args):
    models_path = args["models_path"] if "models_path" in args else os.path.dirname(__file__) + "/models"

    return models_path if os.path.exists(models_path) else None

  def import_models(self, models_path):
    if not models_path:
      return []

    sys.path.insert(0, models_path)

    all_files = os.listdir(models_path)

    models_regex = re.compile(r"\.py$", re.IGNORECASE)

    model_file_names = filter(models_regex.search, all_files)

    model_module_names = map(self.get_model_module_name, model_file_names)
    model_class_names = map(self.get_model_class_name, model_module_names)

    models = []

    for model_module_name, model_class_name in zip(model_module_names, model_class_names):
      model_module = importlib.import_module(model_module_name)

      model_class = model_module.__getattribute__(model_class_name)

      models.append({"class": model_class, "module": model_module})

    return models

  def get_controller_module_name(self, controller_file_name):
    return os.path.splitext(controller_file_name)[0]

  def get_controller_class_name(self, controller_module_name):
    separator_pos = controller_module_name.index("_")

    return controller_module_name[0:separator_pos].capitalize() + controller_module_name[separator_pos + 1:].capitalize()

  def import_controllers(self, controllers_path):
    controllers = []

    sys.path.insert(0, controllers_path)

    all_files = os.listdir(controllers_path)

    controllers_regex = re.compile(r"(.*)_(?:(view|controller))\.py$", re.IGNORECASE)

    controller_file_names = filter(controllers_regex.search, all_files)

    controller_module_names = map(self.get_controller_module_name, controller_file_names)
    controller_class_names = map(self.get_controller_class_name, controller_module_names)

    for controller_module_name, controller_class_name in zip(controller_module_names, controller_class_names):
      controller_module = importlib.import_module(controller_module_name)
      controller_class = controller_module.__getattribute__(controller_class_name)

      controllers.append({"class": controller_class, "module": controller_module})

    return controllers

  def get_route_base(self, controller_class_name):
    # first strip out the -View or -Controller prefix (those are the
    # only we'll get -- we explicitly searched for only those two. see
    # import_controllers
    base_name = re.sub("(?:View|Controller)", "", controller_class_name)
    base_name = base_name.lower()

    singular_base_name = self.inflect.singular_noun(base_name)
    if singular_base_name == False: # already singular
      route_base = self.inflect.plural_noun(base_name)
    else:
      route_base = self.inflect.plural_noun(singular_base_name)

    return route_base

  def is_class_abstract(self, cls):
    abstract_attribute = "__abstract__"

    for base_class in cls.__bases__:
      base_class_is_abstract = getattr(base_class, "__abstract__", False)
      if base_class_is_abstract:
        return False

    # no base class had the __abstract__ attribute, check on the given class
    class_is_abstract = getattr(cls, "__abstract__", False)
    if class_is_abstract:
      return True

    return False

  def setup_inflect_engine(self):
    # use an inflection engine for generating route bases --
    # making plurals of controller names etc.
    self.inflect = inflect.engine()
    self.inflect.classical()

  def inject_models_into_controllers(self, controllers, models):
    for controller in controllers:
      # inject each model into the controller's module so it can be
      # referenced without having to do an import...
      controller_module = controller["module"]
      for model in models:
        model_class = model["class"]

        setattr(controller_module, model_class.__name__, model_class)

  @staticmethod
  def get_http_methods(base_class, cls):
    all_methods = _fc_get_interesting_members(base_class, cls)

    http_methods = [m for m in all_methods if m[0] in ["get", "post", "put", "patch", "delete", "index"]]

    return http_methods

  @staticmethod
  def get_class_methods(base_class, cls):
    all_methods = _fc_get_interesting_members(base_class, cls)

    class_methods = []

    super_classes = cls.__bases__
    for super_class in super_classes:
      class_methods += [m for m in all_methods if m[0] in dir(cls) and not m[0] in dir(super_class)]

    return class_methods

  def register_routes(self, controller_class, app, **kwargs):
    if not self.is_class_abstract(controller_class):
      route_base = controller_class.route_base if controller_class.route_base else self.get_route_base(controller_class.__name__)

    http_only = kwargs.pop("http_only", False)

    fc.get_interesting_members = Router.get_http_methods if http_only else Router.get_class_methods
    controller_class.register(app, route_base=route_base, **kwargs)
    fc.get_interesting_members = _fc_get_interesting_members

  def register_app_with_controllers(self, controllers, app, **kwargs):
    for controller in controllers:
      controller_class = controller["class"]

      self.register_routes(controller_class, app, **kwargs)

  def __init__(self, app, **kwargs):
    self.setup_inflect_engine()

    models = self.import_models(self.get_models_path(kwargs))

    controllers = self.import_controllers(self.get_controllers_path(kwargs))

    self.inject_models_into_controllers(controllers, models)
    self.register_app_with_controllers(controllers, app, **kwargs)

    for rule in app.url_map.iter_rules():
      print rule, rule.defaults, rule.arguments, rule.endpoint
