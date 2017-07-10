from djangofloor.decorators import connect, SerializedForm

from django.template import RequestContext
__author__ = 'Matthieu Gallet'


@connect(path='autoplanner.test_signal')
def test_signal(request):
    return [{'signal': 'df.messages.warning', 'options': {'html': 'This is a server-side message', }, }]
