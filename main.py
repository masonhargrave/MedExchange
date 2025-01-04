# main.py

import os
import json
import requests
from functools import wraps

from flask import Flask, request, jsonify, g
from jose import jwt
from werkzeug.exceptions import HTTPException

from database import engine, SessionLocal, Base
from db_models import DbOrder, DbTrade
from models import Order
from order_book import OrderBook

app = Flask(__name__)
Base.metadata.create_all(bind=engine)

# In-memory order book
order_book = OrderBook()

AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "dev-57rb7zxhlau7kh8o.us.auth0.com")
API_AUDIENCE = os.environ.get("AUTH0_API_AUDIENCE", "https://medexchange")
ALGORITHMS = ["RS256"]


class AuthError(Exception):
    def __init__(self, error, status_code):
        super().__init__(error)
        self.error = error
        self.status_code = status_code


@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return jsonify({"error": e.name, "description": e.description}), e.code


def get_token_auth_header():
    auth_header = request.headers.get("Authorization", None)
    if not auth_header:
        raise AuthError(
            {
                "code": "authorization_header_missing",
                "description": "Authorization header is expected",
            },
            401,
        )

    parts = auth_header.split()
    if parts[0].lower() != "bearer":
        raise AuthError(
            {
                "code": "invalid_header",
                "description": "Authorization header must start with Bearer",
            },
            401,
        )
    elif len(parts) == 1:
        raise AuthError(
            {"code": "invalid_header", "description": "Token not found"}, 401
        )
    elif len(parts) > 2:
        raise AuthError(
            {
                "code": "invalid_header",
                "description": "Authorization header must be Bearer token",
            },
            401,
        )

    token = parts[1]
    return token


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_auth_header()
        try:
            jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
            jwks_data = requests.get(jwks_url).json()
            unverified_header = jwt.get_unverified_header(token)
            rsa_key = {}
            for key in jwks_data["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"],
                    }
                    break
            if not rsa_key:
                raise AuthError(
                    {
                        "code": "invalid_header",
                        "description": "Unable to find appropriate key",
                    },
                    401,
                )

            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer=f"https://{AUTH0_DOMAIN}/",
            )
        except jwt.ExpiredSignatureError:
            raise AuthError(
                {"code": "token_expired", "description": "token is expired"}, 401
            )
        except jwt.JWTClaimsError:
            raise AuthError(
                {
                    "code": "invalid_claims",
                    "description": "incorrect claims. please check the audience and issuer",
                },
                401,
            )
        except Exception:
            raise AuthError(
                {
                    "code": "invalid_header",
                    "description": "Unable to parse authentication token.",
                },
                401,
            )

        g.top.current_user = payload
        return f(*args, **kwargs)

    return decorated


@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Welcome to MedExchange with Auth0-secured endpoints!"})


@app.route("/orders", methods=["POST"])
@requires_auth
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400
    user_id = data.get("user_id")
    side = data.get("side")
    price = data.get("price")
    quantity = data.get("quantity")
    if not all([user_id, side, price, quantity]):
        return jsonify({"error": "Missing required fields"}), 400
    new_order = Order(
        order_id=os.urandom(16).hex(),
        user_id=user_id,
        side=side,
        price=float(price),
        quantity=int(quantity),
    )
    trades = order_book.add_order(new_order)
    return (
        jsonify(
            {
                "message": "Order created",
                "order": new_order.__dict__,
                "trades_executed": [t.__dict__ for t in trades],
            }
        ),
        200,
    )


@app.route("/order_book", methods=["GET"])
def get_order_book():
    return jsonify(order_book.get_order_book()), 200


@app.route("/trades", methods=["GET"])
def get_trades():
    return jsonify(order_book.get_trade_history()), 200


if __name__ == "__main__":
    app.run(debug=True)
