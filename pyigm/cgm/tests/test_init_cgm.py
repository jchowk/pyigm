# Module to run tests on generating IGMSystem

from __future__ import print_function, absolute_import, division, unicode_literals

# TEST_UNICODE_LITERALS

import pytest
import numpy as np
import io
import json

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.cosmology import Planck15 as cosmo

from ..cgm import CGM, CGMAbsSys
from ..cgmsurvey import CGMAbsSurvey
from ..utils import cgm_from_galaxy_igmsystems
from pyigm.field.galaxy import Galaxy
from pyigm.abssys.igmsys import IGMSystem
from pyigm.igm.igmsightline import IGMSightline
import pyigm

import pdb
from pkg_resources import resource_filename

def simple_cgmabssys():
    radec = (125.0*u.deg, 45.2*u.deg)
    gal = Galaxy(radec,z=0.3)
    radec_qso = (125.0*u.deg, 45.203*u.deg)
    igmsys = IGMSystem(radec_qso, gal.z, [-500,500]*u.km/u.s, abs_type='CGM')
    # Instantiate
    cgmabs = CGMAbsSys(gal, igmsys, cosmo=cosmo)
    return cgmabs

def test_init_cgm():
    # Simple properties
    radec = SkyCoord(ra=123.1143*u.deg, dec=-12.4321*u.deg)
    gal = Galaxy(radec,z=0.3)
    cgm = CGM(gal)
    # Test
    np.testing.assert_allclose(cgm.galaxy.z, 0.3)

def test_init_cgmabssys():
    # Instantiate
    cgmabs = simple_cgmabssys()
    # Test
    np.testing.assert_allclose(cgmabs.rho.value, 49.6141071, rtol=1e-5)

def test_init_cgmabssurvey():
    cgmsurvey = CGMAbsSurvey(survey='cos-halos', ref='Tumlinson+13, Werk+13')
    # Test
    assert cgmsurvey.survey == 'cos-halos'


def test_p11_survey():
    p11_tarfile = resource_filename('pyigm', '/data/CGM/P11/P11_sys.tar')
    p11 = CGMAbsSurvey.from_tarball(p11_tarfile, chk_lowz=False, chk_z=False, build_sys=True)
    assert len(p11.cgm_abs[2].igm_sys._components) == 2


def test_init_cgmabssurvey_from_abssys():
    # Instantiate abssys and survey
    cgmabs = simple_cgmabssys()
    cgmsurvey = CGMAbsSurvey.from_cgmabssys([cgmabs,cgmabs])
    # Test
    assert len(cgmsurvey.cgm_abs) == 2

def test_get_cgmsys():
    # Instantiate abssys and survey
    cgmabs1 = simple_cgmabssys()
    cgmabs2 = simple_cgmabssys()
    cgmabs1.name = 'System1'
    cgmabs2.name = 'System2'
    cgmsurvey = CGMAbsSurvey.from_cgmabssys([cgmabs1, cgmabs2])
    retsys = cgmsurvey.get_cgmsys('System2')
    assert isinstance(retsys,CGMAbsSys)

def test_to_dict():
    # Instantiate
    cgmabs = simple_cgmabssys()
    # Test
    cdict = cgmabs.to_dict()
    assert isinstance(cdict,dict)
    for key in ['Name', 'z', 'rho', 'cosmo', 'galaxy', 'igm_sys']:
        assert key in cdict.keys()

def test_read_write_json():
    cgmabs = simple_cgmabssys()
    # Write
    cgmabs.write_json('tmp.json')
    # Read
    cgmabs2 = CGMAbsSys.from_json('tmp.json')
    np.testing.assert_allclose(cgmabs2.rho.value, 49.6141071, rtol=1e-5)

def test_cgm_from_igmsystems():
    # Load sightlines
    sl_file = pyigm.__path__[0]+'/data/sightlines/Blind_CIV/J115120.46+543733.08.json'
    igmsl = IGMSightline.from_json(sl_file)
    igmsys = igmsl.make_igmsystems(vsys=400*u.km/u.s)
    # Galaxy
    galaxy = Galaxy((178.84787, 54.65734), z=0.00283)
    # Go
    cgm_list = cgm_from_galaxy_igmsystems(galaxy, igmsys, cosmo=cosmo, correct_lowz=False)
    assert len(cgm_list) == 1
    np.testing.assert_allclose(cgm_list[0].rho.value, 127.8324005876)

def test_cgm_from_igmsystems_lowz():
    # Load sightlines
    sl_file = pyigm.__path__[0]+'/data/sightlines/Blind_CIV/J115120.46+543733.08.json'
    igmsl = IGMSightline.from_json(sl_file)
    igmsys = igmsl.make_igmsystems(vsys=400*u.km/u.s)
    # Galaxy
    galaxy = Galaxy((178.84787, 54.65734), z=0.00283)
    # Go
    cgm_list = cgm_from_galaxy_igmsystems(galaxy, igmsys, cosmo=cosmo, correct_lowz=True)
    assert len(cgm_list) == 1
    np.testing.assert_allclose(cgm_list[0].rho.value, 188.80894355281708)
