from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, HTML
from crispy_forms.bootstrap import FormActions

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


class EasySetupForm(forms.Form):
    num_cobos = forms.IntegerField(label='Number of CoBos',
                                   help_text='CoBos will be numbered sequentially starting at 0.')
    one_ecc_server = forms.BooleanField(required=False, label='Use one ECC server for all sources?',
                                        help_text='This includes the MuTAnT, if present.')

    first_cobo_ecc_ip = forms.GenericIPAddressField(protocol='IPv4', label='IP address of first CoBo ECC server')
    first_cobo_data_router_ip = forms.GenericIPAddressField(protocol='IPv4', label='IP address of first CoBo data router')

    mutant_is_present = forms.BooleanField(required=False, label='Is there a MuTAnT?',
                                           help_text='The next two fields are only required if the MuTAnT is present.')
    mutant_ecc_ip = forms.GenericIPAddressField(protocol='IPv4', required=False, label='IP address of MuTAnT ECC server')
    mutant_data_router_ip = forms.GenericIPAddressField(protocol='IPv4', required=False, label='IP address of MuTAnT data router')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'easy-setup-form'
        self.helper.form_method = 'post'

        general_help = """
            <div>
                <p>Use this form to quickly set up the system with some default values. Note that this will
                replace the current configuration of the system if it's already set up.</p>
            </div>
        """

        ip_help = """
            <div>
                <p>The next two fields configure the IP addresses for the CoBos. The first CoBo will get an
                ECC server and data router with these IP addresses. This first address will then be incremented
                by one for each remaining CoBo.</p>

                <p>Note that if there is only one ECC server, the ECC server IP address entered below will apply
                to all CoBos and the MuTAnT, if present.</p>
            </div>
        """

        delete_warning = """
            <div class='alert alert-danger'>
                <strong>Warning:</strong> Submitting this form will remove all ECC servers, data routers, and data sources from
                the system and replace them with new ones!
            </div>
        """

        self.helper.layout = Layout(
            HTML(general_help),
            Fieldset(
                'CoBo setup',
                'num_cobos',
                'one_ecc_server',
                HTML(ip_help),
                'first_cobo_ecc_ip',
                'first_cobo_data_router_ip',
            ),
            Fieldset(
                'MuTAnT setup',
                'mutant_is_present',
                'mutant_ecc_ip',
                'mutant_data_router_ip',
            ),
            HTML(delete_warning),
            FormActions(Submit('submit', 'Submit'))
        )

    def clean(self):
        super().clean()

        mutant_is_present = self.cleaned_data['mutant_is_present']
        mutant_ecc_ip = self.cleaned_data['mutant_ecc_ip']
        mutant_data_router_ip = self.cleaned_data['mutant_data_router_ip']
        one_ecc_server = self.cleaned_data['one_ecc_server']

        if mutant_is_present and ((not one_ecc_server and mutant_ecc_ip == '') or mutant_data_router_ip == ''):
            raise forms.ValidationError('Must provide ECC and data router IP for MuTAnT if MuTAnT is present')
