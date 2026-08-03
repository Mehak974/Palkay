from django.db import models

class Experiment(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ExperimentVariant(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=50) # e.g. "Control", "Variant A"
    weight = models.PositiveIntegerField(default=50, help_text="Weight percentage (e.g. 50)")

    def __str__(self):
        return f"{self.experiment.name} - {self.name}"

class Participant(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='participants')
    variant = models.ForeignKey(ExperimentVariant, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, db_index=True)
    user = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL)
    converted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('experiment', 'session_key')
