from app import app

from flask_classy import FlaskView

class Controller(FlaskView):
    def render_object(self, o):
        return o
