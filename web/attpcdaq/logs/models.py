from django.db import models


class LogEntry(models.Model):

    class Meta:
        verbose_name_plural = 'Log entries'

    logger_name = models.CharField(max_length=100)
    create_time = models.DateTimeField()
    level_number = models.IntegerField()
    level_name = models.CharField(max_length=20)
    path_name = models.CharField(max_length=200)
    line_num = models.IntegerField()
    function_name = models.CharField(max_length=200)
    message = models.TextField()

    def __str__(self):
        return 'Log entry: {level} - {src} - {time}'.format(level=self.level_name,
                                                            src=self.logger_name,
                                                            time=self.create_time)
