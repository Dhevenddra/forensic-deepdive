"""FastAPI handler fixture (DEC-059) — a Depends injection on the service tail.

trace('create_owner', downstream) walks: create_owner →INJECTS→ save_owner
→CALLS→ Owner →PERSISTS_TO→ table::owners.
"""

from fastapi import Depends

from repo import save_owner


def create_owner(svc=Depends(save_owner)):
    return svc()
