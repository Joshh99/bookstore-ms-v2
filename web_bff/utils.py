import jwt
from datetime import datetime

def validate_jwt(token: str) -> bool:
    try:
        # Decode without signature verification as per specs
        payload = jwt.decode(token, options={"verify_signature": False})
        sub = payload.get("sub")
        if sub not in ["starlord", "gamora", "drax", "rocket", "groot"]:
            return False
        exp = payload.get("exp")
        if not exp or datetime.now().timestamp() > exp:
            return False
        iss = payload.get("iss")
        if iss != "cmu.edu":
            return False
        return True
    except jwt.DecodeError:
        return False