from django import template
from django.db import models
from django.db.models import Count

from templatetag_sugar.register import tag
from templatetag_sugar.parser import Name, Variable, Constant, Optional, Model

from taggit.managers import TaggableManager
from taggit.models import TaggedItem, Tag
from taggit import settings

T_MAX = getattr(settings, 'TAGCLOUD_MAX', 6.0)
T_MIN = getattr(settings, 'TAGCLOUD_MIN', 1.0)

register = template.Library()

def get_queryset(forvar=None):
    if None == forvar:
        # get all tags
        queryset = Tag.objects.all()
    else:
        # extract app label and model name
        beginning, applabel, model = None, None, None
        try:
            beginning, applabel, model = forvar.rsplit('.', 2)
        except ValueError:
            try:
                applabel, model = forvar.rsplit('.', 1)
            except ValueError:
                applabel = forvar
        
        # filter tagged items        
        if applabel:
            queryset = TaggedItem.objects.filter(content_type__app_label=applabel)
        if model:
            queryset = queryset.filter(content_type__model=model)
            
        # get tags
        tag_ids = queryset.values_list('tag_id', flat=True)
        queryset = Tag.objects.filter(id__in=tag_ids)
    return queryset.annotate(num_times=Count('taggit_taggeditem_items'))

def get_weight_fun(t_min, t_max, f_min, f_max):
    def weight_fun(t_i, t_min=t_min, t_max=t_max, f_min=f_min, f_max=f_max):
        return f_max * ((t_i-t_min)/(t_max-t_min))
    return weight_fun

@tag(register, [Constant('as'), Name(), Optional([Constant('for'), Variable()])])
def get_taglist(context, asvar, forvar=None):
    queryset = get_queryset(forvar)         
    queryset = queryset.order_by('-num_times')        
    context[asvar] = queryset
    return ''

@tag(register, [Constant('as'), Name(), Optional([Constant('for'), Variable()])])
def get_tagcloud(context, asvar, forvar=None):
    queryset = get_queryset(forvar)
    num_times = queryset.values_list('num_times', flat=True)
    weight_fun = get_weight_fun(T_MIN, T_MAX, min(num_times), max(num_times))
    for tag in queryset:
        tag.weight = weight_fun(tag.num_times)
    context[asvar] = queryset.order_by('name')
    return ''
    
def tag_include(forvar):
    return {'forvar': forvar}
    
register.inclusion_tag('taggit_templatetags/taglist_include.html')(tag_include)
register.inclusion_tag('taggit_templatetags/tagcloud_include.html')(tag_include)