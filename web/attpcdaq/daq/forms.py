from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, HTML
from crispy_forms.bootstrap import FormActions, AppendedText

from .models import DataSource, ECCServer, DataRouter, Experiment, ConfigId, RunMetadata, Observable, Measurement


class CrispyModelFormBase(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'

        self.helper.add_input(Submit('submit', 'Submit'))


class DataSourceForm(CrispyModelFormBase):
    class Meta:
        model = DataSource
        fields = ['name', 'ecc_server', 'data_router']


class ECCServerForm(CrispyModelFormBase):
    class Meta:
        model = ECCServer
        fields = ['name', 'ip_address', 'port', 'log_path', 'config_root', 'config_backup_root']

    def save(self, commit=True):
        instance = super().save(commit=False)
        current_expt = Experiment.objects.get(is_active=True)
        instance.experiment = current_expt
        instance.save()
        self.save_m2m()
        return instance


class DataRouterForm(CrispyModelFormBase):
    class Meta:
        model = DataRouter
        fields = ['name', 'ip_address', 'port', 'connection_type', 'log_path']

    def save(self, commit=True):
        instance = super().save(commit=False)
        current_expt = Experiment.objects.get(is_active=True)
        instance.experiment = current_expt
        instance.save()
        self.save_m2m()
        return instance


class ConfigSelectionForm(CrispyModelFormBase):
    """A form used to select a config file set for an ECC server."""
    class Meta:
        model = ECCServer
        fields = ['selected_config']
        help_texts = {
            'selected_config': 'Name is given as "describe/prepare/configure" triple.'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['selected_config'].queryset = ConfigId.objects.filter(ecc_server=self.instance)


class ExperimentForm(CrispyModelFormBase):
    class Meta:
        model = Experiment
        fields = ['name']


class ExperimentChoiceForm(forms.Form):
    experiment = forms.ModelChoiceField(queryset=Experiment.objects.all(), label='Choose experiment')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        new_expt_btn_html = """
        <a href='{% url "daq/new_experiment" %}' class='btn btn-success btn-block'>New experiment</a>
        """
        self.helper.layout = Layout(
            'experiment',
            Submit('submit', 'Load experiment', css_class='btn btn-primary btn-block'),
            HTML("<p class='text-center'>or</h3>"),
            HTML(new_expt_btn_html),
        )


class NewExperimentForm(forms.ModelForm):
    class Meta:
        model = Experiment
        fields = ['name']
        labels = {'name': 'Experiment name'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Create experiment', css_class='btn btn-primary btn-block'))

    def save(self, commit=True):
        """Override to make the new experiment the active one."""
        instance = super().save(commit=False)
        instance.is_active = True
        instance.save()
        self.save_m2m()

        return instance


class RunMetadataForm(CrispyModelFormBase):
    class Meta:
        model = RunMetadata
        fields = ['run_number', 'run_class', 'title', 'start_datetime', 'stop_datetime', 'config_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        observables = Observable.objects.filter(experiment=self.instance.experiment)

        field_type_map = {
            Observable.INTEGER: forms.IntegerField,
            Observable.FLOAT: forms.FloatField,
            Observable.STRING: forms.CharField,
        }

        for obs in observables:
            measurement, created = Measurement.objects.get_or_create(run_metadata=self.instance, observable=obs)
            field_type = field_type_map[obs.value_type]
            self.fields[obs.name] = field_type(initial=measurement.value, required=False, help_text=obs.comment)

        # Build form layout
        self.helper.inputs = None  # Override default input provided by base class
        run_fieldset = Fieldset(
            'Run information',
            *self.Meta.fields
        )
        measurement_fieldset = Fieldset(
            'Measurements',
            *(AppendedText(obs.name, obs.units) if obs.units else obs.name for obs in observables)
        )
        prepop_btn_html = """
            <a href="{{% url 'daq/update_run_metadata' {:d} %}}?prepopulate=True"
               class='btn btn-default'>
                Fill from last run
            </a>
        """.format(self.instance.pk)
        buttons = FormActions(
            Submit('submit', 'Submit'),
            HTML(prepop_btn_html),
        )
        self.helper.layout = Layout(
            run_fieldset,
            measurement_fieldset,
            buttons,
        )

    def save(self, commit=True):
        for name, value in self.cleaned_data.items():
            if name in self.Meta.fields:
                continue

            observable = Observable.objects.get(name=name, experiment=self.instance.experiment)
            measurement = Measurement.objects.get(run_metadata=self.instance, observable=observable)
            measurement.value = value
            measurement.save()

        return super().save(commit=commit)


class ObservableForm(CrispyModelFormBase):
    class Meta:
        model = Observable
        fields = ['name', 'value_type', 'units', 'comment']
        help_texts = {
            'comment': 'This comment will be shown on the run sheet next to the field for this measurement.',
        }

    def __init__(self, *args, **kwargs):
        self.disabled_fields = kwargs.pop('disabled_fields', [])
        super().__init__(*args, **kwargs)

        for field_name in self.disabled_fields:
            try:
                self.fields[field_name].disabled = True
            except KeyError:
                raise ValueError('Cannot disable field {:s} which does not exist.'.format(field_name)) from None


class DataSourceListUploadForm(forms.Form):
    data_source_list = forms.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'datasource-list-upload-form'
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Submit'))


class EasySetupForm(forms.Form):
    # General fields
    num_cobos = forms.IntegerField(label='Number of CoBos',
                                   help_text='CoBos will be numbered sequentially starting at 0.')
    one_ecc_server = forms.BooleanField(required=False, label='Use one ECC server for all sources?',
                                        help_text='This includes the MuTAnT, if present.')

    # CoBo configuration fields
    first_cobo_ecc_ip = forms.GenericIPAddressField(protocol='IPv4', label='IP address of first CoBo ECC server')
    first_cobo_data_router_ip = forms.GenericIPAddressField(protocol='IPv4',
                                                            label='IP address of first CoBo data router')
    cobo_ecc_log_file_location = forms.CharField(max_length=500, label='Location of CoBo ECC server log files')
    cobo_router_log_file_location = forms.CharField(max_length=500, label='Location of CoBo data router log files')
    cobo_config_root = forms.CharField(max_length=500, label='Location of CoBo config files')
    cobo_config_backup_root = forms.CharField(max_length=500, label='CoBo config file backup destination')

    # MuTAnT configuration fields
    mutant_is_present = forms.BooleanField(required=False, label='Is there a MuTAnT?',
                                           help_text='The remaining fields are only required if the MuTAnT is present.')
    mutant_ecc_ip = forms.GenericIPAddressField(protocol='IPv4', required=False,
                                                label='IP address of MuTAnT ECC server')
    mutant_data_router_ip = forms.GenericIPAddressField(protocol='IPv4', required=False,
                                                        label='IP address of MuTAnT data router')
    mutant_ecc_log_file_location = forms.CharField(max_length=500, required=False,
                                                   label='Location of MuTAnT ECC server log files')
    mutant_router_log_file_location = forms.CharField(max_length=500, required=False,
                                                      label='Location of MuTAnT data router log files')
    mutant_config_root = forms.CharField(max_length=500, required=False,
                                         label='Location of MuTAnT config files')
    mutant_config_backup_root = forms.CharField(max_length=500, required=False,
                                                label='MuTAnT config file backup destination')

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

        config_file_help = """
            <div>
                <p>The next fields set the paths to config files and log files. These paths are <em>on
                the remote computer</em> where the GET software is running. These paths will be applied
                to each ECC server and data router created, so if they are not the same for each CoBo,
                they will need to be edited manually later.</p>

                <div class='alert alert-warning'>
                    <strong>Note:</strong> These must be <em>full paths</em>, and they may not contain '~'.
                </div>
            </div>
        """

        delete_warning = """
            <div class='alert alert-danger'>
                <strong>Warning:</strong> Submitting this form will remove all ECC servers, data routers, and data sources from
                this experiment and replace them with new ones!
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
                HTML(config_file_help),
                'cobo_ecc_log_file_location',
                'cobo_router_log_file_location',
                'cobo_config_root',
                'cobo_config_backup_root',
            ),
            Fieldset(
                'MuTAnT setup',
                'mutant_is_present',
                'mutant_ecc_ip',
                'mutant_data_router_ip',
                'mutant_ecc_log_file_location',
                'mutant_router_log_file_location',
                'mutant_config_root',
                'mutant_config_backup_root',
            ),
            HTML(delete_warning),
            FormActions(Submit('submit', 'Submit'))
        )

    def clean(self):
        super().clean()

        if self.cleaned_data['mutant_is_present']:
            if not self.cleaned_data['one_ecc_server'] and self.cleaned_data['mutant_ecc_ip'] == '':
                raise forms.ValidationError('Must provide ECC IP for MuTAnT if MuTAnT is present')
            if self.cleaned_data['mutant_data_router_ip'] == '':
                raise forms.ValidationError('Must provide router IP for MuTAnT if MuTAnT is present')
            if self.cleaned_data['mutant_ecc_log_file_location'] == '':
                raise forms.ValidationError('Must provide ECC log file path for MuTAnT if MuTAnT is present')
            if self.cleaned_data['mutant_router_log_file_location'] == '':
                raise forms.ValidationError('Must provide data router log file path for MuTAnT if MuTAnT is present')
            if self.cleaned_data['mutant_config_root'] == '':
                raise forms.ValidationError('Must provide config file directory for MuTAnT if MuTAnT is present')
            if self.cleaned_data['mutant_config_backup_root'] == '':
                raise forms.ValidationError('Must provide config file backup root for MuTAnT if MuTAnT is present')
