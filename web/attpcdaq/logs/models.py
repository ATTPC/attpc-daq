from django.db import models


class LogEntry(models.Model):
    name = models.CharField(max_length=100)
    create_time = models.DateTimeField()
    level_number = models.IntegerField()
    level_name = models.CharField(max_length=20)
    path_name = models.CharField(max_length=200)
    line_num = models.IntegerField()
    function_name = models.CharField(max_length=200)
    message = models.TextField()
