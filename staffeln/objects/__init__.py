from .queue import Queue
from .volume import Volume

# from volume import Volume


def register_all():
    __import__('staffeln.objects.volume')
    __import__('staffeln.objects.queue')
