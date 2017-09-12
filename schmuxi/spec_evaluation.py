'''Turns your raw txt-spectrum of spectra into graphics for your labbook or
publication
'''
# import numpy as np
import pandas as pd
import yaml
from glob import glob
from os import chdir
import os
import matplotlib.pyplot as plt
import re
from autofind_paras import find_parameters


default_config = "spec_config.yml"


class Experiment:
    '''Represents an experimental session and contains parameters and methods
    to process and publish its results'''
    def auto_config(self, config_source):
        """creates a dictionary of configuration parameters out of given path"""
        config = None

        # fallback to default config if no file can be found
        try:
            config = self.load_config(config_source)
        except IOError:
            print("No configuration-file found. Using default-configuration.")
            try:
                config = self.load_config(os.path.dirname(os.abspath(__file__))+"/"+default_config)
            except IOError:
                print("Someone messed with the default-configuration file. It cannot be found.")
            else: return(config)
        else: return(config)


    def load_config(self, config_source):
        """loads yml-file and turns it into a dict"""
        with open(config_source, 'r') as configfile:
            config = yaml.load(configfile)

        return(config)

    def __init__(
        self,
        auto_config = True,
        config_source = "spec_config.yml",
        source = os.getcwd(),
        working_dir = os.getcwd(),
        seperator = " ",
        background = 0,
        convert_to_energy = "TRUE",
        convert_to_rate = "TRUE",
        normalize = "FALSE",
        exposure = 0,
        cosmic_cycles = 5,
        cosmic_factor = 10,
        cosmic_distance = 5,
        reference = None):
        '''initializies experimental parameters and
        processing-configuration.'''

        if auto_config is True:

            try:
                config = self.auto_config(config_source)
            except:
                print("Auto-Configuration failed.")
            else:
                self.config = config
                self.working_dir = config["general"]["working_dir"]
                self.seperator = config["spec_paras"]["seperator"]
                self.background = config["spec_paras"]["background"]
                self.convert_to_energy = config["spec_paras"]["convert_to_energy"]
                self.convert_to_rate = config["spec_paras"]["convert_to_rate"]
                self.normalize = config["spec_paras"]["normalize"]
                self.source = config["general"]["source_path"]
                self.exposure = config["spec_paras"]["exposure"]

                self.cosmic_cycles = config["auto_paras"]["cosmic_cycles"]
                self.cosmic_factor = config["auto_paras"]["cosmic_factor"]
                self.cosmic_distance = config["auto_paras"]["cosmic_distance"]

                self.reference = config["reference"]["name"]
        else:
                self.working_dir = working_dir
                self.seperator = seperator
                self.background = background
                self.convert_to_energy = convert_to_energy
                self.convert_to_rate = convert_to_rate
                self.normalize = normalize
                self.source = source
                self.exposure = exposure

                self.cosmic_cycles = cosmic_cycles
                self.cosmic_factor = cosmic_factor
                self.cosmic_distance = cosmic_distance

                self.reference = reference
        self.spectra = list_of_spectra(source)

    def load_file(self, filename, seperator):
        '''reads a csv-file into a pandas.Dataframe'''
        spectrum = pd.read_csv(filename, seperator, header=None)

        return(spectrum)


    def list_of_spectra(self, source):
        '''Checks the filenames of txt-files to find Data corresponding to single
        spectra.'''
        chdir(source)
        files_list = glob('*.txt')

        # does not include spectral maps.
        spectra = [entry for entry in files_list if "DCmap" not in entry]

        return(spectra)

# def background



    def cosmic_erase(
        spectrum,
        cosmic_cycles,
        cosmic_distance,
        cosmic_factor):
        '''Routine for erasing "cosmics", random high intensity peaks'''
        for i in range(cosmic_cycles):
            if spectrum.iat[spectrum.idxmax()[1], 1] > cosmic_factor * spectrum.iat[spectrum.idxmax()[1]+cosmic_distance, 1]:
                spectrum.set_value(spectrum.idxmax()[1], list(spectrum)[1], (spectrum.iat[spectrum.idxmax()[1]-cosmic_distance,1] + spectrum.iat[spectrum.idxmax()[1]+cosmic_distance, 1]))

        return(spectrum)



    def plot_spectrum(spec, cfg, source):
        '''plots a single spectrum into png-file of the same name, according to the experimental configuration.
    
        Can read the experimental parameters from the filename or use global
        parameters'''
        #use auto_parameters.py to find parameters in the file name
        parameters = find_parameters(spec, cfg)

        #spectrum = pd.read_csv(source + spec)
        spectrum = load_file(source + spec)

        spectrum.columns = ["Wavelength [nm]","Intensity [arb.]"]
        #spectrum = spectrum.set_index("Wavelength [nm]")
        print(spectrum.head(5))

        spectrum['Intensity [arb.]'] = spectrum['Intensity [arb.]'] - background

        spectrum = cosmic_erase(
            spectrum,
            cosmic_cycles,
            cosmic_distance,
            cosmic_factor)


    if convert_to_energy == ('TRUE' or 'true'):
        print(list(spectrum))
        spectrum.rename(columns={"Wavelength [nm]": 'Energy [eV]'}, inplace=True)
        print(spectrum.head(5))
        spectrum['Energy [eV]'] = 1239.82/spectrum['Energy [eV]']
        spectrum = spectrum.sort_values("Energy [eV]", axis=0)
        spectrum.set_index("Energy [eV]", inplace=True)
    else:
        spectrum.set_index("Wavelength [nm]", inplace=True)
    if normalize == ('TRUE' or 'true'):
        spectrum.rename(columns={list(spectrum)[0]: "Intensity [norm.]"}, inplace=True)
        spectrum = spectrum/spectrum.max()
    elif convert_to_rate == ('TRUE' or 'true'):
        if re.match(".*[0-9]*s.*", spec):
            exposure = float(re.search("[0-9]*s", spec).group()[:-1])
            print(exposure)
        spectrum.rename(columns={"Intensity [arb.]": "Counts p.s."}, inplace=True)
        spectrum = spectrum/exposure

    plt.style.use('classic')
    #plot_spectrum = spectrum.plot.line(legend=False)
    plot_spectrum = spectrum.plot.line()

    if cfg["reference"]["use"] == ('TRUE' or 'true' or 'True'):

        reference_plot = load_file(source + reference)
        reference_plot.columns = ["Energy","Intensity"]
        reference_plot["Energy"] = reference_plot["Energy"] + cfg["reference"]["offset"]
        reference_plot.set_index(list(reference_plot)[0], inplace=True)
        reference_plot.plot(ax=plot_spectrum)

        mylabels = [cfg["reference"]["plot_name"], cfg["reference"]["ref_name"]]
        plot_spectrum.legend(labels=mylabels)

    plot_spectrum.set_xlabel(spectrum.index.name)
    plot_spectrum.set_ylabel(list(spectrum)[0])
    yloc = plt.MaxNLocator(3)
    plot_spectrum.yaxis.set_major_locator(yloc)
    print(spectrum.index[0])

    plot_spectrum.set_xlim(left=spectrum.index[0], right=spectrum.index[-1])

    count = 0
    for i, j in parameters.items():
        plt.text(spectrum.index[10],spectrum.max()*(0.95-0.05*count), i)
        plt.text(spectrum.index[300],spectrum.max()*(0.95-0.05*count), j)
        count = count + 1
        print(count)
    fig = plot_spectrum.get_figure()
    fig.savefig(spec[:-4] + '.png')



def plot_all_spectra(source):
    '''"One-Click"-function to publish every spectrum in the
    working-directory'''
    for spec in list_of_spectra(source):
        plot_spectrum(spec, cfg, source)

if __name__ == '__main__':
    Session = Experiment()
    plot_all_spectra(source)