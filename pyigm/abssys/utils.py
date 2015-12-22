""" Utilities for IGMSystem and IGMSurvey
Best to keep these separate from the Class modules
"""
from __future__ import print_function, absolute_import, division, unicode_literals

# Python 2 & 3 compatibility
try:
    basestring
except NameError:
    basestring = str

import pdb
import numpy as np
from collections import OrderedDict

from astropy import constants as const
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import QTable
from astropy.io import ascii

from linetools.spectralline import AbsLine
from linetools.analysis import absline as ltaa
from linetools.isgm.abscomponent import AbsComponent


def parse_datdict(datdict):
    """ Parse a datdict

    Parameters
    ----------
    datdict : OrderedDict
      dict from .dat file

    Returns
    -------
    tuple of coord, zabs, name, NHI, sigNHI, clmfil
    """
    # RA/DEC
    try:
        ras, decs = (datdict['RA (2000)'], datdict['DEC (2000)'])
    except KeyError:
        ras, decs = ('00 00 00', '+00 00 00')
    coord = SkyCoord(ras, decs, frame='icrs', unit=(u.hour, u.deg))

    # zabs
    try:
        zabs = float(datdict['zabs'])
    except KeyError:
        zabs = 0.

    # Name
    name = ('J' +
                 coord.ra.to_string(unit=u.hour, sep='', pad=True) +
                 coord.dec.to_string(sep='', pad=True, alwayssign=True) +
                 '_z{:0.3f}'.format(zabs))

    # NHI
    try:
        NHI = float(datdict['NHI'])  # DLA format
    except KeyError:
        try:
            NHI = float(datdict['NHI tot'])  # LLS format
        except KeyError:
            NHI = 0.

    # NHIsig
    try:
        key_sigNHI = datdict['sig(NHI)']  # DLA format
    except KeyError:
        try:
            key_sigNHI = datdict['NHI sig']  # LLS format
        except KeyError:
            key_sigNHI = '0.0 0.0'
    sigNHI = np.array(map(float,key_sigNHI.split()))

    # Abund file
    try:
        key_clmfil = datdict['Abund file']  # DLA format
    except KeyError:
        key_clmfil = ''
    clm_fil = key_clmfil.strip()

    # Return
    return coord, zabs, name, NHI, sigNHI, clm_fil


def read_all_file(all_file, components=None, verbose=False):
    """Read in JXP-style .all file in an appropriate manner

    NOTE: If program breaks in this function, check the all file
    to see if it is properly formatted.

    Fills components if inputted
    May need to worry more about CII*

    Parameters
    ----------
    all_file : str
      Full path to the .all file
    components : list, optional
      List of AbsComponent objects
    verbose : bool, optional
    """
    # Read
    if verbose:
        print('Reading {:s}'.format(all_file))
    names = ('Z', 'ion', 'logN', 'sig_logN', 'flag_N', 'flg_inst')  # was using flg_clm
    table = ascii.read(all_file, format='no_header', names=names)

    # Fill components
    if components is not None:
        allZ = np.array([comp.Zion[0] for comp in components])
        allion = np.array([comp.Zion[1] for comp in components])
        allEj = np.array([comp.Ej.value for comp in components])
        # Loop
        for row in table:
            mt = np.where((allZ == row['Z']) & (allion == row['ion']) & (allEj == 0.))[0]
            if len(mt) == 0:
                pass
            elif len(mt) == 1:
                # Fill
                components[mt[0]].flag_N = row['flag_N']
                components[mt[0]].logN = row['logN']
                components[mt[0]].sig_logN = row['sig_logN']
            else:
                raise ValueError("Found multiple component matches in read_all_file")
    # Write
    return table


def read_clmfile(clm_file, linelist=None):
    """ Read in a .CLM file in an appropriate manner

    NOTE: If program breaks in this function, check the clm to see if it is properly formatted.


    RETURNS two dictionaries CLM and LINEDIC. CLM contains the contents of CLM
    for the given DLA. THe LINEDIC that is passed (when not None) is updated appropriately.

    Keys in the CLM dictionary are:
      INST - Instrument used
      FITS - a list of fits files
      ZABS - absorption redshift
      ION - .ION file location
      HI - THe HI column and error; [HI, HIerr]
      FIX - Any abundances that need fixing from the ION file
      VELS - Dictioanry of velocity limits, which is keyed by
        FLAGS - Any measurment flags assosicated with VLIM
        VLIM - velocity limits in km/s [vmin,vmax]
        ELEM - ELement (from get_elem)

    See get_elem for properties of LINEDIC

    Parameters
    ----------
    clm_file : str
      Full path to the .clm file
    linelist : LineList
      can speed up performance
    """
    clm_dict = {}
    # Read file
    f=open(clm_file, 'r')
    arr=f.readlines()
    f.close()
    nline = len(arr)
    # Data files
    clm_dict['flg_data'] = int(arr[1][:-1])
    clm_dict['fits_files']={}
    ii = 2
    for jj in range(0,6):
        if (clm_dict['flg_data'] % (2**(jj+1))) > (2**jj - 1):
            clm_dict['fits_files'][2**jj] = arr[ii].strip()
            ii += 1

    # Redshift
    clm_dict['zsys']=float(arr[ii][:-1]) ; ii += 1
    clm_dict['ion_fil']=arr[ii].strip() ; ii += 1
    # NHI
    tmp = arr[ii].split(','); ii += 1
    if len(tmp) != 2:
        raise ValueError('ionic_clm: Bad formatting {:s} in {:s}'.format(arr[ii-1], clm_file))
    clm_dict['NHI']=float(tmp[0])
    clm_dict['sigNHI']=float(tmp[1])
    # Abundances by hand
    numhand=int(arr[ii][:-1]); ii += 1
    clm_dict['fixabund'] = {}
    if numhand > 0:
        for jj in range(numhand):
            # Atomic number
            atom = int(arr[ii][:-1]) ; ii += 1
            # Values
            tmp = arr[ii].strip().split(',') ; ii += 1
            clm_dict['fixabund'][atom] = float(tmp[0]), float(tmp[1]), int(tmp[2])
    # Loop on lines
    clm_dict['lines'] = {}
    while ii < (nline-1):
        # No empty lines allowed
        if len(arr[ii].strip()) == 0:
           break
        # Read flag
        ionflg = int(arr[ii].strip()); ii += 1
        # Read the rest
        tmp = arr[ii].split(',') ; ii += 1
        if len(tmp) != 4:
            raise ValueError('ionic_clm: Bad formatting {:s} in {:s}'.format(arr[ii-1],clm_file))
        vmin = float(tmp[1].strip())
        vmax = float(tmp[2].strip())
        key = float(tmp[0].strip()) # Using a numpy float not string!
        # Generate
        clm_dict['lines'][key] = AbsLine(key*u.AA,closest=True,linelist=linelist)
        clm_dict['lines'][key].attrib['z'] = clm_dict['zsys']
        clm_dict['lines'][key].analy['FLAGS'] = ionflg, int(tmp[3].strip())
        # By-hand
        if ionflg >= 8:
            clm_dict['lines'][key].attrib['N'] = 10.**vmin / u.cm**2
            clm_dict['lines'][key].attrib['sig_N'] = (10.**(vmin+vmax) - 10.**(vmin-vmax))/2/u.cm**2
        else:
            clm_dict['lines'][key].analy['vlim']= [vmin,vmax]*u.km/u.s
    # Return
    return clm_dict


def read_dat_file(dat_file):
    """ Read an ASCII ".dat" file from JXP format 'database'

    Parameters
    ----------
    dat_file : str
     filename

    Returns
    -------
    dat_dict : OrderedDict
      A dict containing the info in the .dat file
    """
    # Define
    datdict = OrderedDict()
    # Open
    f = open(dat_file, 'r')
    for line in f:
        tmp = line.split('! ')
        tkey = tmp[1].strip()
        key = tkey
        val = tmp[0].strip()
        datdict[key] = val
    f.close()

    return datdict


def read_ion_file(ion_fil, components, lines=None, linelist=None, tol=0.05*u.AA):
    """ Read in JXP-style .ion file in an appropriate manner

    NOTE: If program breaks in this function, check the .ion file
    to see if it is properly formatted.

    If components is passed in, these are filled as applicable.

    Parameters
    ----------
    ion_fil : str
      Full path to .ion file
    components : list
      List of AbsComponent objects
    lines : list, optional
      List of AbsLine objects [used for historical reasons, mainly]
    linelist : LineList
      May speed up performance
    tol : Quantity, optional
      Tolerance for matching wrest
    """
    # Read
    names = ('wrest', 'logN', 'sig_logN', 'flag_N', 'flg_inst')
    table = ascii.read(ion_fil, format='no_header', names=names)

    # Generate look-up table for quick searching
    all_wv = []
    all_idx = []
    for jj,comp in enumerate(components):
        for kk,iline in enumerate(comp._abslines):
            all_wv.append(iline.wrest)
            all_idx.append((jj,kk))
    all_wv = u.Quantity(all_wv)
    # Loop now
    for row in table:
        mt = np.where(np.abs(all_wv-row['wrest']*u.AA)<tol)[0]
        if len(mt) == 0:
            pass
        elif len(mt) == 1:
            # Fill
            jj = all_idx[mt[0]][0]
            kk = all_idx[mt[0]][1]
            components[jj]._abslines[kk].attrib['flag_N'] = row['flag_N']
            components[jj]._abslines[kk].attrib['logN'] = row['logN']
            components[jj]._abslines[kk].attrib['sig_logN'] = row['sig_logN']
            components[jj]._abslines[kk].analy['flg_inst'] = row['flg_inst']
        else:
            pdb.set_trace()
            raise ValueError("Matched multiple lines in read_ion_file")
    # Return
    return table

