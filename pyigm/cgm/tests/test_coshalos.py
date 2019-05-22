# Module to run tests on initializing AbslineSystem

# TEST_UNICODE_LITERALS

import numpy as np
import os, pdb

import pytest
remote_data = pytest.mark.remote_data

from astropy.table import Table

from pyigm.cgm.cos_halos import COSHalos#, COSDwarfs

def data_path(filename):
    data_dir = os.path.join(os.path.dirname(__file__), 'files')
    return os.path.join(data_dir, filename)

'''
def test_load_kin():
    # Class
    cos_halos = COSHalos()
    cos_halos.load_mega(skip_ions=True)
    # Load kin
    cos_halos.load_abskin()
'''


def test_PDF():
    cos_halos = COSHalos()
    cos_halos.load_mtl_pdfs()
    all_NHI = []
    all_mtl = []
    for sl, sightline in enumerate(cos_halos.cgm_abs):
        if sightline.igm_sys.NHIPDF is not None:
            this_nhi = sightline.igm_sys.NHIPDF.median
            all_NHI.append(this_nhi)
            all_mtl.append(sightline.igm_sys.metallicity.median)
    # Test
    assert len(all_NHI) == 31

def test_load_sngl():
    # Class
    cos_halos = COSHalos(fits_path=data_path(''), cdir=data_path(''), load=False)
    # Load
    cos_halos.load_single_fits(('J0950+4831', '177_27'))

def test_write_sngl():
    import io, json
    from linetools import utils as ltu
    # Class
    cos_halos = COSHalos(fits_path=data_path(''), cdir=data_path(''), load=False)
    # Load
    cos_halos.load_single_fits(('J0950+4831', '177_27'))
    # Write to JSON
    cdict = cos_halos.cgm_abs[0].to_dict()
    ltu.savejson('tmp.json', cdict, overwrite=True)

"""
def test_load_sngl_dwarf():
    # Class
    cos_dwarfs = COSDwarfs(fits_path=data_path(''), kin_init_file='dum', cdir='dum')
    # Load
    cos_dwarfs.load_single( ('J0042-1037', '358_9'))
"""

def test_load_survey():
    # Class
    cos_halos = COSHalos()#debug=True)
    assert len(cos_halos.cgm_abs) == 44
    # Metallicity
    cos_halos.load_mtl_pdfs()
    # Confirm  J0943+0531_227_19 is out for metallicity
    cgm_j0943 = cos_halos[('J0943+0531','227_19')]
    assert cgm_j0943.igm_sys.metallicity is None


def test_getitem():
    # Class
    cos_halos = COSHalos(fits_path=data_path(''), cdir='dum', load=False)
    # Load
    cos_halos.load_single_fits(('J0950+4831', '177_27'))
    # Get item
    cgm_abs = cos_halos[('J0950+4831','177_27')]
    assert cgm_abs.galaxy.field == 'J0950+4831'

