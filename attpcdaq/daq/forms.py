from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import DataSource, DataRouter, ECCServer, Experiment


class DataSourceForm(ModelForm):
    class Meta:
        model = DataSource
        fields = ['name', 'ecc_server', 'data_router', 'config']

    def __init__(self, *args, **kwargs):
        super(DataSourceForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'add-source-form'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))


class DataRouterForm(ModelForm):
    class Meta:
        model = DataRouter
        fields = ['name', 'ip_address', 'port', 'type']

    def __init__(self, *args, **kwargs):
        super(DataRouterForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'add-data-router-form'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))


class ECCServerForm(ModelForm):
    class Meta:
        model = ECCServer
        fields = ['name', 'ip_address', 'port']

    def __init__(self, *args, **kwargs):
        super(ECCServerForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'add-ecc-server-form'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))


class ExperimentSettingsForm(ModelForm):
    class Meta:
        model = Experiment
        fields = ['name', 'target_run_duration']

    def __init__(self, *args, **kwargs):
        super(ExperimentSettingsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'experiment-settings-form'
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Submit'))
