from flask import Blueprint, Flask

app = Flask(__name__)
bp = Blueprint("api", __name__, url_prefix="/api")


@app.route("/users/<int:user_id>", methods=["GET", "POST"])
def get_user(user_id):
    return user_id


@app.route("/health")
def health():
    return "ok"


@bp.route("/items")
def list_items():
    return []


@bp.post("/items")
def create_item():
    return {}


app.register_blueprint(bp)
