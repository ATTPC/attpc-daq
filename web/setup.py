from setuptools import setup

setup(name='AT-TPC DAQ Controller',
      version='0.1',
      description='New GUI for AT-TPC DAQ system',
      author='Joshua Bradt',
      author_email='bradt@nscl.msu.edu',
      requires=['django>=1.9',
                'django-crispy-forms',
                'paramiko',
                'celery',
                'zeep']
      )
