from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import DataSource, Experiment, ConfigId, RunMetadata


class DataSourceForm(ModelForm):
    class Meta:
        model = DataSource
        fields = ['name', 'ecc_ip_address', 'ecc_port', 'data_router_ip_address', 'data_router_port',
                  'data_router_type']

    def __init__(self, *args, **kwargs):
        super(DataSourceForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'add-source-form'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))


class ConfigSelectionForm(ModelForm):
    class Meta:
        model = DataSource
        fields = ['selected_config']

    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'config-selection-form'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))

        self.fields['selected_config'].queryset = ConfigId.objects.filter(data_source=self.instance)


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


class RunMetadataForm(ModelForm):
    class Meta:
        model = RunMetadata
        fields = ['title']

    def __init__(self, *args, **kwargs):
        super(RunMetadataForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'runmetadata-form'
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Submit'))
