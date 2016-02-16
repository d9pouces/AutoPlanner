# -*- coding: utf-8 -*-
from django import template
from django.utils.safestring import mark_safe

__author__ = 'Matthieu Gallet'

register = template.Library()
metro_colors = {'black', 'white', 'lime', 'green', 'emerald', 'teal', 'blue', 'cyan', 'cobalt', 'indigo', 'violet',
                'pink', 'magenta', 'crimson', 'red', 'orange', 'amber', 'yellow', 'brown', 'olive', 'steel', 'mauve',
                'taupe', 'gray', 'dark', 'darker', 'darkBrown', 'darkCrimson', 'darkMagenta', 'darkIndigo', 'darkCyan',
                'darkCobalt', 'darkTeal', 'darkEmerald', 'darkGreen', 'darkOrange', 'darkRed', 'darkPink', 'darkViolet',
                'darkBlue', 'lightBlue', 'lightRed', 'lightGreen', 'lighterBlue', 'lightTeal', 'lightOlive',
                'lightOrange', 'lightPink', 'grayDark', 'grayDarker', 'grayLight', 'grayLighter', }


@register.simple_tag
def metro_icon(name, large=False, color=None, animation=None):
    if isinstance(large, int) and 2 <= large <= 4:
        large = ' mif-%dx' % large
    elif large:
        large = ' mif-lg'
    else:
        large = ''
    if color in metro_colors:
        color_cls = 'fg-' + color
        color = ''
    else:
        color_cls = ''
    if animation:
        assert animation in ('spin', 'pulse', 'spanner', 'bell', 'vertical', 'horizontal', 'flash', 'bounce', 'float',
                             'heartbeat', 'shake', 'shuttle', 'pass', 'ripple')
    return mark_safe('<span class="mif-icon_{name}{large}{ani}{color_cls}"{color}></span>'.format(
        name=name,
        large=large,
        ani='mif-ani-%s' % animation if animation else '',
        color_cls=color_cls,
        color='style="color:%s;"' % color if color else ''
    ))
