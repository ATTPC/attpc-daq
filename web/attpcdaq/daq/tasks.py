"""Celery asynchronous tasks for the daq module."""

import os
from django.conf import settings
from zeep.client import Client as SoapClient
from zeep.helpers import serialize_object
from celery import shared_task


class EccClient(object):

    def __init__(self, address):
        wsdl_url = os.path.join(settings.BASE_DIR, 'attpcdaq', 'daq', 'ecc.wsdl')
        client = SoapClient(wsdl_url)
        self.service = client.create_service('{urn:ecc}ecc', 'http://{}:8083'.format(address))

        self.operations = ['GetState',
                           'Describe',
                           'Prepare',
                           'Configure',
                           'Start',
                           'Stop',
                           'Undo',
                           'Breakup',
                           'GetConfigIDs']

    def __getattr__(self, item):
        if item in self.operations:
            def wrapper(*args):
                return serialize_object(getattr(self.service, item)(*args))
            return wrapper

        else:
            raise AttributeError('EccClient has no attribute {}'.format(item))


@shared_task
def ecc_request(url, action, *args):
    client = EccClient(url)
    return getattr(client, action)(*args)
