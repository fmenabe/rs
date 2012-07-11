from django.db import models

# Create your models here.
class Hosts(models.Model):
    fqdn = models.CharField(max_length=64, null=False)
    username = models.CharField(max_length=64, null=True)
    password = models.CharField(max_length=64, null=True)


class Schedules(models.Model):
    host = models.ForeignKey('Hosts', null=False)
    user = models.CharField(max_length=32, null=False)
    path = models.CharField(max_length=255, null=False)
    hours = models.CharField(max_length=32, null=False)
    minutes = models.CharField(max_length=32, null=False)
    dom = models.CharField(max_length=32, null=False)
    mon = models.CharField(max_length=32, null=False)
    dow = models.CharField(max_length=32, null=False)


class Results(models.Model):
    schedule = models.ForeignKey('Schedules')
    date = models.DateField(null=False)
    return_code = models.SmallIntegerField(null=False)
    stdout = models.TextField()
    stderr = models.TextField()

