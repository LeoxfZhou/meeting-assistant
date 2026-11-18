"""Local administrator command; never automatically promote the first registrant."""
import argparse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.db.session import build_engine
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    engine = build_engine(Settings().database_url.get_secret_value())
    try:
        with Session(engine) as session:
            user = session.scalar(select(User).where(User.email == args.email.casefold()))
            if user is None:
                parser.error("Register the user first")
            user.is_owner = True
            session.commit()
            print("Owner role assigned to the selected registered user.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
