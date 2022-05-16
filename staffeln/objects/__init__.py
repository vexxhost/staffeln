from .queue import Queue  # noqa: F401
from .volume import Volume  # noqa: F401


# from volume import Volume
def register_all():
    __import__("staffeln.objects.volume")
    __import__("staffeln.objects.queue")
