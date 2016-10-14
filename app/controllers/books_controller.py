from app import app

from controller import Controller

class BooksController(Controller):
  def __init__(self):
    Controller.__init__(self)

  def get(self):
    b = "Hello books"
    return self.render_object(b)

  def undefined(self):
    return "this is an undefined route"
