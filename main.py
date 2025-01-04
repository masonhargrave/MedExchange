# main.py

import os
import requests
from flask import Flask, request, jsonify, g
from functools import wraps
from jose import jwt
from werkzeug.exceptions import HTTPException

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import config
from database import engine, Base
from models import Order
from order_book import OrderBook

Base.metadata.create_all(bind=engine)

app = Flask(__name__)
app.config.from_object(config.get_config())

storage_uri = os.environ.get("RATE_LIMIT_STORAGE_URI", "memory://")
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri=storage_uri,
    default_limits=app.config["RATE_LIMITS"],
)

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

    return parts[1]


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_auth_header()
        print(f"Token received: {token}")  # Debugging

        try:
            # Fetch JWKS
            jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
            jwks_data = requests.get(jwks_url, timeout=10).json()
            unverified_header = jwt.get_unverified_header(token)

            # Find the matching RSA key
            rsa_key = next(
                (
                    {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"],
                    }
                    for key in jwks_data["keys"]
                    if key["kid"] == unverified_header["kid"]
                ),
                None,
            )

            if not rsa_key:
                print("RSA key not found")  # Debugging
                raise AuthError(
                    {
                        "code": "invalid_header",
                        "description": "Unable to find appropriate key",
                    },
                    401,
                )

            # Validate and decode the token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer=f"https://{AUTH0_DOMAIN}/",
            )
            print(f"Token payload: {payload}")  # Debugging

        except jwt.ExpiredSignatureError:
            raise AuthError(
                {"code": "token_expired", "description": "Token is expired"}, 401,
            )
        except jwt.JWTClaimsError:
            raise AuthError(
                {
                    "code": "invalid_claims",
                    "description": "Incorrect claims. Check audience and issuer.",
                },
                401,
            )
        except Exception as e:
            print(f"JWT validation error: {e}")  # Debugging
            raise AuthError(
                {
                    "code": "invalid_header",
                    "description": "Unable to parse authentication token.",
                },
                401,
            )

        g.current_user = payload
        return f(*args, **kwargs)

    return decorated


order_book = OrderBook()


@app.route("/")
@limiter.exempt
def index():
    return jsonify(
        {
            "message": "MedExchange: Auth0-protected endpoints with rate limiting",
            "environment": os.environ.get("FLASK_ENV", "development"),
            "rate_limits": app.config["RATE_LIMITS"],
        }
    )


@app.route("/orders", methods=["POST"])
@requires_auth
@limiter.limit("10/minute")
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
    # Set debug dynamically based on the environment
    app.run(debug=os.getenv("FLASK_ENV", "development") == "development")
