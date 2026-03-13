import os
import sys
import logging
from pathlib import Path
from datetime import datetime

from kiteconnect import KiteConnect
from dotenv import set_key, load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import KITE_API_KEY, KITE_API_SECRET, KITE_ACCESS_TOKEN

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
logging.basicConfig(level=logging.INFO, format="%(asctime)s [KITE-AUTH] %(message)s")
log = logging.getLogger(__name__)


def get_kite_client() -> KiteConnect:
    """
    Return an authenticated KiteConnect session.
    Flow:
      1. Try existing access_token from env.
      2. If expired / missing → prompt for request_token → exchange → store.
    """
    kite = KiteConnect(api_key=KITE_API_KEY)

    if KITE_ACCESS_TOKEN:
        kite.set_access_token(KITE_ACCESS_TOKEN)
        if _is_session_valid(kite):
            log.info("Reused existing access_token — session alive.")
            return kite
        log.warning("Stored access_token is expired; starting re-auth.")

    return _do_oauth(kite)


def _is_session_valid(kite: KiteConnect) -> bool:
    """Ping the profile endpoint to verify the session."""
    try:
        kite.profile()
        return True
    except Exception as exc:
        log.debug("Session check failed: %s", exc)
        return False


def _do_oauth(kite: KiteConnect) -> KiteConnect:
    """
    Perform the full OAuth 2.0 handshake.
    Opens login URL → user pastes back the request_token.
    """
    login_url = kite.login_url()
    print("\n" + "═" * 60)
    print("  Open this URL in your browser and log in:")
    print(f"  {login_url}")
    print("═" * 60)
    print("  After login, Kite redirects to your redirect URI with")
    print("  ?request_token=<TOKEN>&action=login&status=success")
    print("  Copy the request_token value and paste it below.\n")

    request_token = input("  request_token › ").strip()
    if not request_token:
        raise ValueError("request_token cannot be empty.")

    data = kite.generate_session(request_token, api_secret=KITE_API_SECRET)
    access_token: str = data["access_token"]

    load_dotenv(ENV_FILE)
    set_key(str(ENV_FILE), "KITE_ACCESS_TOKEN", access_token)
    os.environ["KITE_ACCESS_TOKEN"] = access_token

    kite.set_access_token(access_token)
    log.info("New session created. Token stored in .env  [user=%s]", data.get("user_name", "—"))
    return kite


def invalidate_session() -> None:
    """Clear the stored access_token (e.g., on explicit logout)."""
    set_key(str(ENV_FILE), "KITE_ACCESS_TOKEN", "")
    log.info("Access token cleared.")


if __name__ == "__main__":
    kite = get_kite_client()
    profile = kite.profile()
    print(f"\n✓ Logged in as: {profile['user_name']} ({profile['email']})")
    print(f"  Broker : {profile['broker']}")
    print(f"  TS     : {datetime.now().isoformat()}")
