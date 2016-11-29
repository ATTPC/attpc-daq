from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
import json

from .models import DataSource, ECCServer, DataRouter, Experiment, ConfigId, RunMetadata


class DataSourceForm(forms.ModelForm):
    class Meta:
        model = DataSource
        fields = ['name', 'ecc_server', 'data_router']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'add-source-form'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))


class ECCServerForm(forms.ModelForm):
    class Meta:
        model = ECCServer
        fields = ['name', 'ip_address', 'port', 'log_path']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'add-ecc-server-form'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))


class DataRouterForm(forms.ModelForm):
    class Meta:
        model = DataRouter
        fields = ['name', 'ip_address', 'port', 'connection_type', 'log_path']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'add-data-router-form'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))


class ConfigSelectionForm(forms.ModelForm):
    """A form used to select a config file set for an ECC server."""
    class Meta:
        model = ECCServer
        fields = ['selected_config']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'config-selection-form'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))

        self.fields['selected_config'].queryset = ConfigId.objects.filter(ecc_server=self.instance)


class ExperimentSettingsForm(forms.ModelForm):
    class Meta:
        model = Experiment
        fields = ['name', 'target_run_duration']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'experiment-settings-form'
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Submit'))


class RunMetadataForm(forms.ModelForm):
    class Meta:
        model = RunMetadata
        fields = ['title']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'runmetadata-form'
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Submit'))


class DataSourceListUploadForm(forms.Form):
    data_source_list = forms.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'datasource-list-upload-form'
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Submit'))
