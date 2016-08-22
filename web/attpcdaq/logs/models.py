from django.db import models
import logging


class LogEntry(models.Model):

    class Meta:
        verbose_name_plural = 'Log entries'

    logger_name = models.CharField(max_length=100)
    create_time = models.DateTimeField()
    path_name = models.CharField(max_length=200)
    line_num = models.IntegerField()
    function_name = models.CharField(max_length=200)
    message = models.TextField()
    traceback = models.TextField(null=True, blank=True)

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    LEVEL_CHOICES = ((DEBUG, 'Debug'),
                     (INFO, 'Info'),
                     (WARNING, 'Warning'),
                     (ERROR, 'Error'),
                     (CRITICAL, 'Critical'))
    LEVEL_DICT = dict(LEVEL_CHOICES)

    level = models.IntegerField(choices=LEVEL_CHOICES)

    def __str__(self):
        return 'Log entry: {level} - {src} - {time}'.format(level=self.get_level_display(),
                                                            src=self.logger_name,
                                                            time=self.create_time)

    @property
    def level_css_class_name(self):
        class_dict = {
            self.WARNING: 'warning',
            self.ERROR: 'danger',
            self.CRITICAL: 'danger',
        }

        return class_dict.get(self.level, '')
