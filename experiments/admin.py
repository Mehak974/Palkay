from django.contrib import admin
from .models import Experiment, ExperimentVariant, Participant
from unfold.admin import ModelAdmin, TabularInline

class ExperimentVariantInline(TabularInline):
    model = ExperimentVariant
    extra = 2

@admin.register(Experiment)
class ExperimentAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_editable = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ExperimentVariantInline]

@admin.register(Participant)
class ParticipantAdmin(ModelAdmin):
    list_display = ('experiment', 'variant', 'session_key', 'user', 'converted', 'created_at')
    list_filter = ('experiment', 'variant', 'converted')
