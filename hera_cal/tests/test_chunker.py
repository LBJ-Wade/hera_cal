# -*- coding: utf-8 -*-
# Copyright 2021 the HERA Project
# Licensed under the MIT License

import pytest
import glob
from pyuvdata import UVData
from pyuvdata import UVCal
from ..data import DATA_PATH
from .. import chunker
from hera_qm.utils import apply_yaml_flags
import numpy as np
import sys

def test_chunk_data_files(tmpdir):
    # list of data files:
    tmp_path = tmpdir.strpath
    data_files = sorted(glob.glob(DATA_PATH + '/zen.2458044.*.uvh5'))
    nfiles = len(data_files)
    # form chunks with three samples.
    for chunk in range(0, nfiles, 2):
        output = tmp_path + f'/chunk.{chunk}.uvh5'
        chunker.chunk_data_files(data_files, data_files[chunk], output, 2,
                                polarizations=['ee'], spw_range=[0, 32],
                                throw_away_flagged_bls=True, ant_flag_yaml=DATA_PATH + '/test_input/a_priori_flags_sample_noflags.yaml')

    # test that chunked files contain identical data (when combined)
    # to original combined list of files.
    # load in chunks
    chunks = sorted(glob.glob(tmp_path + '/chunk.*.uvh5'))
    uvd = UVData()
    uvd.read(chunks)
    # load in original file
    uvdo = UVData()
    uvdo.read(data_files, freq_chans=range(32))
    apply_yaml_flags(uvdo, DATA_PATH + '/test_input/a_priori_flags_sample_noflags.yaml', throw_away_flagged_ants=True,
                     flag_freqs=False, flag_times=False, ant_indices_only=True)
    assert np.all(np.isclose(uvdo.data_array, uvd.data_array))
    assert np.all(np.isclose(uvdo.flag_array, uvd.flag_array))
    assert np.all(np.isclose(uvdo.nsample_array, uvd.nsample_array))

def test_chunk_cal_files(tmpdir):
    # list of data files:
    tmp_path = tmpdir.strpath
    cal_files = sorted(glob.glob(DATA_PATH + '/test_input/*.abs.calfits_54x_only.part*'))
    nfiles = len(cal_files)
    # form chunks with three samples.
    for chunk in range(0, nfiles, 2):
        output = tmp_path + f'/chunk.{chunk}.calfits'
        chunker.chunk_cal_files(cal_files, cal_files[chunk], output, 2)

    # test that chunked files contain identical data (when combined)
    # to original combined list of files.
    # load in chunks
    chunks = sorted(glob.glob(tmp_path + '/chunk.*.calfits'))
    uvc = UVCal()
    uvc.read_calfits(chunks)
    # load in original file
    uvco = UVCal()
    uvco.read_calfits(cal_files)

    assert np.all(np.isclose(uvco.gain_array, uvc.gain_array))
    assert np.all(np.isclose(uvco.flag_array, uvc.flag_array))

def test_chunk_data_parser():
    sys.argv = [sys.argv[0], 'a', 'b', 'c', 'input', 'output', '3']
    ap = chunker.chunk_data_parser()
    args = ap.parse_args()
    assert args.filenames == ['a', 'b', 'c']
    assert args.inputfile == 'input'
    assert args.outputfile == 'output'
    assert args.chunk_size == 3

def test_chunk_cal_parser():
    sys.argv = [sys.argv[0], 'a', 'b', 'c', 'input', 'output', '3']
    ap = chunker.chunk_cal_parser()
    args = ap.parse_args()
    assert args.filenames == ['a', 'b', 'c']
    assert args.inputfile == 'input'
    assert args.outputfile == 'output'
    assert args.chunk_size == 3
