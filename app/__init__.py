from flask import Flask

from router import Router

app = Flask(__name__)

router = Router(app, trailing_slash=False)
