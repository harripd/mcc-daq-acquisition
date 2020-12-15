import phconvert as phc

import numpy as np

def write_file(timestamps, detectors, timestamps_unit, fname='measurements'):

    """
    METADATA
    """

    identity = dict(
        author="Gabriel Moya, Philipp Klocke",
        author_affiliation="LMU PSB Group")


    measurement_specs = dict(
        measurement_type = 'smFRET',
        detectors_specs = {'spectral_ch1': [0],  # list of donor's detector IDs
                           'spectral_ch2': [1]}  # list of acceptor's detector IDs
        )


    photon_data = dict(
        timestamps=timestamps,
        detectors=detectors,
        timestamps_specs={'timestamps_unit': timestamps_unit},
        measurement_specs=measurement_specs)


    setup = dict(
        ## Mandatory fields
        num_pixels = 2,                   # using 2 detectors
        num_spots = 1,                    # a single confoca excitation
        num_spectral_ch = 2,              # donor and acceptor detection 
        num_polarization_ch = 1,          # no polarization selection 
        num_split_ch = 1,                 # no beam splitter (TODO ?)
        modulated_excitation = False,     # CW excitation, no modulation 
        excitation_alternated = [False],  # CW excitation, no modulation 
        lifetime = False,                 # no TCSPC in detection
        
        ## Optional fields
        excitation_wavelengths = [532e-9],         # List of excitation wavelenghts
        excitation_cw = [True],                    # List of booleans, True if wavelength is CW
        detection_wavelengths = [580e-9, 640e-9],  # Nominal center wavelength 
                                                   # each for detection ch
    )


    data = dict(
        description="Whatever you measured here... ^^",
        photon_data = photon_data,
        setup=setup,
        identity=identity,
    )

    """
    Actually saving the file
    """
    phc.hdf5.save_photon_hdf5(data, h5_fname=f'{fname}.h5', overwrite=True)

