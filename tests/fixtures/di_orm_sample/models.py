"""SQLAlchemy model fixture (DEC-059) — the ORM tail terminal."""


class Owner(Base):
    __tablename__ = "owners"

    def name(self):
        return "owner"
