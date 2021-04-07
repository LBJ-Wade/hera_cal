# -*- coding: utf-8 -*-
# Copyright 2019 the HERA Project
# Licensed under the MIT License

import pytest
import numpy as np
from copy import deepcopy
import os
import sys
import shutil
from scipy import constants
from pyuvdata import UVCal, UVData

from .. import io
from .. import tfrf
from ..data import DATA_PATH
import glob
from .. import vis_clean
from .. import utils as utils
from pyuvdata import UVFlag


class Test_TophatFRFilter(object):
    def test_run_tophat_frfilter(self):
        fname = os.path.join(DATA_PATH, "zen.2458043.12552.xx.HH.uvORA")
        k = (24, 25, 'ee')
        tfrfil = tfrf.TophatFRFilter(fname, filetype='miriad')
        tfrfil.read(bls=[k])
        bl = np.linalg.norm(tfrfil.antpos[24] - tfrfil.antpos[25]) / constants.c * 1e9
        sdf = (tfrfil.freqs[1] - tfrfil.freqs[0]) / 1e9

        tfrfil.run_tophat_frfilter(to_filter=tfrfil.data.keys(), tol=1e-2, output_prefix='frfiltered')
        for k in tfrfil.data.keys():
            assert tfrfil.frfiltered_resid[k].shape == (60, 64)
            assert tfrfil.frfiltered_model[k].shape == (60, 64)
            assert k in tfrfil.frfiltered_info

        # test skip_wgt imposition of flags
        fname = os.path.join(DATA_PATH, "zen.2458043.12552.xx.HH.uvORA")
        k = (24, 25, 'ee')
        # check successful run when avg_red_bllens is True and when False.
        for avg_red_bllens in [True, False]:
            tfrfil = tfrf.TophatFRFilter(fname, filetype='miriad')
            tfrfil.read(bls=[k])
            if avg_red_bllens:
                tfrfil.avg_red_baseline_vectors()
            wgts = {k: np.ones_like(tfrfil.flags[k], dtype=np.float)}
            wgts[k][:, 0] = 0.0
            tfrfil.run_tophat_frfilter(to_filter=[k], weight_dict=wgts, tol=1e-5, window='blackman-harris', skip_wgt=0.1, maxiter=100)
            assert tfrfil.clean_info[k]['status']['axis_0'][0] == 'skipped'
            np.testing.assert_array_equal(tfrfil.clean_flags[k][:, 0], np.ones_like(tfrfil.flags[k][:, 0]))
            np.testing.assert_array_equal(tfrfil.clean_model[k][:, 0], np.zeros_like(tfrfil.clean_resid[k][:, 0]))
            np.testing.assert_array_equal(tfrfil.clean_resid[k][:, 0], np.zeros_like(tfrfil.clean_resid[k][:, 0]))

    def test_load_tophat_frfilter_and_write_baseline_list(self, tmpdir):
        tmp_path = tmpdir.strpath
        uvh5 = [os.path.join(DATA_PATH, "test_input/zen.2458101.46106.xx.HH.OCR_53x_54x_only.first.uvh5"),
                os.path.join(DATA_PATH, "test_input/zen.2458101.46106.xx.HH.OCR_53x_54x_only.second.uvh5")]
        cals = [os.path.join(DATA_PATH, "test_input/zen.2458101.46106.xx.HH.uv.abs.calfits_54x_only.part1"),
                os.path.join(DATA_PATH, "test_input/zen.2458101.46106.xx.HH.uv.abs.calfits_54x_only.part2")]
        outfilename = os.path.join(tmp_path, 'temp.h5')
        cdir = os.path.join(tmp_path, 'cache_temp')
        # make a cache directory
        if os.path.isdir(cdir):
            shutil.rmtree(cdir)
        os.mkdir(cdir)
        # check graceful exist with length zero baseline list.
        with pytest.warns(RuntimeWarning):
            xf.load_xtalk_filter_and_write(datafile_list=uvh5, baseline_list=[], polarizations=['ee'],
                                           calfile_list=cals, spw_range=[100, 200], cache_dir=cdir,
                                           read_cache=True, write_cache=True, avg_red_bllens=True,
                                           res_outfilename=outfilename, clobber=True,
                                           mode='dayenu')
        for avg_bl in [True, False]:
            tfrf.load_tophat_frfilter_and_write(datafile_list=uvh5, baseline_list=[(53, 54, 'ee')],
                                                calfile_list=cals, spw_range=[100, 200], cache_dir=cdir,
                                                read_cache=True, write_cache=True, avg_red_bllens=avg_bl,
                                                res_outfilename=outfilename, clobber=True,
                                                mode='dayenu')
            hd = io.HERAData(outfilename)
            d, f, n = hd.read()
            assert len(list(d.keys())) == 1
            assert d[(53, 54, 'ee')].shape[1] == 100
            assert d[(53, 54, 'ee')].shape[0] == 60
            # now do no spw range and no cal files just to cover those lines.
            tfrf.load_tophat_frfilter_and_write(datafile_list=uvh5, baseline_list=[(53, 54, 'ee')],
                                                cache_dir=cdir,
                                                read_cache=True, write_cache=True, avg_red_bllens=avg_bl,
                                                res_outfilename=outfilename, clobber=True,
                                                mode='dayenu')
            hd = io.HERAData(outfilename)
            d, f, n = hd.read()
            assert len(list(d.keys())) == 1
            assert d[(53, 54, 'ee')].shape[1] == 1024
            assert d[(53, 54, 'ee')].shape[0] == 60

        # test baseline_list = None
        xf.load_xtalk_filter_and_write(datafile_list=uvh5, baseline_list=None,
                                       calfile_list=cals, spw_range=[100, 200], cache_dir=cdir,
                                       read_cache=True, write_cache=True, avg_red_bllens=True,
                                       res_outfilename=outfilename, clobber=True,
                                       mode='dayenu')
        hd = io.HERAData(outfilename)
        d, f, n = hd.read()
        assert d[(53, 54, 'ee')].shape[1] == 100
        assert d[(53, 54, 'ee')].shape[0] == 60
        hdall = io.HERAData(uvh5)
        hdall.read()
        assert np.allclose(hd.baseline_array, hdall.baseline_array)
        assert np.allclose(hd.time_array, hdall.time_array)
        # now test flag factorization and time thresholding.
        # prepare an input files for broadcasting flags
        uvh5 = os.path.join(DATA_PATH, "test_input/zen.2458101.46106.xx.HH.OCR_53x_54x_only.uvh5")
        input_file = os.path.join(tmp_path, 'temp_special_flags.h5')
        shutil.copy(uvh5, input_file)
        hd = io.HERAData(input_file)
        _, flags, _ = hd.read()
        ntimes_before = hd.Ntimes
        nfreqs_before = hd.Nfreqs
        freqs_before = hd.freqs
        times_before = hd.times
        for bl in flags:
            flags[bl][:] = False
            flags[bl][0, :hd.Nfreqs // 2] = True  # first time has 50% flagged
            flags[bl][-3:, -1] = True  # last channel has flags for three integrations
        hd.update(flags=flags)
        hd.write_uvh5(input_file, clobber=True)
        # this time_threshold will result in
        # entire first integration begin flagged
        # and entire final channel being flagged
        # when flags are broadcasted.
        time_thresh = 2. / hd.Ntimes
        for blnum, bl in enumerate(flags.keys()):
            outfilename = os.path.join(tmp_path, 'bl_chunk_%d.h5' % blnum)
            tfrf.load_tophat_frfilter_and_write(datafile_list=[input_file], res_outfilename=outfilename,
                                                tol=1e-4, baseline_list=[bl],
                                                cache_dir=cdir,
                                                factorize_flags=True,
                                                time_thresh=time_thresh, clobber=True)
        # now load all of the outputs in
        output_files = glob.glob(tmp_path + '/bl_chunk_*.h5')
        hd = io.HERAData(output_files)
        d, f, n = hd.read()
        hd_original = io.HERAData(uvh5)
        for bl in hd_original.bls:
            assert bl in d.keys()

        for bl in f:
            assert np.all(f[bl][:, -1])
            assert np.all(f[bl][0, :])

        # test apriori flags and flag_yaml
        flag_yaml = os.path.join(DATA_PATH, 'test_input/a_priori_flags_sample.yaml')
        uvf = UVFlag(hd, mode='flag', copy_flags=True)
        uvf.to_waterfall(keep_pol=False, method='and')
        uvf.flag_array[:] = False
        flagfile = os.path.join(tmp_path, 'test_flag.h5')
        uvf.write(flagfile, clobber=True)
        tfrf.load_tophat_frfilter_and_write(datafile_list=[input_file], res_outfilename=outfilename,
                                            tol=1e-4, baseline_list=[bl[:2]],
                                            clobber=True, mode='dayenu',
                                            external_flags=flagfile, overwrite_flags=True)
        # test that all flags are False
        hd = io.HERAData(outfilename)
        d, f, n = hd.read()
        for k in f:
            assert np.all(~f[k])
        # now do the external yaml
        tfrf.load_tophat_frfilter_and_write(datafile_list=[input_file], res_outfilename=outfilename,
                                            tol=1e-4, baseline_list=[bl[:2]],
                                            clobber=True, mode='dayenu',
                                            external_flags=flagfile, overwrite_flags=True,
                                            flag_yaml=flag_yaml)
        # test that all flags are af yaml flags
        hd = io.HERAData(outfilename)
        d, f, n = hd.read()
        for k in f:
            assert np.all(f[k][:, 0])
            assert np.all(f[k][:, 1])
            assert np.all(f[k][:, 10:20])
            assert np.all(f[k][:, 60])
        os.remove(outfilename)
        shutil.rmtree(cdir)

    def test_load_tophat_frfilter_and_write(self, tmpdir):
        tmp_path = tmpdir.strpath
        uvh5 = os.path.join(DATA_PATH, "test_input/zen.2458101.46106.xx.HH.OCR_53x_54x_only.uvh5")
        outfilename = os.path.join(tmp_path, 'temp.h5')
        tfrf.load_tophat_frfilter_and_write(uvh5, res_outfilename=outfilename, tol=1e-4, clobber=True, Nbls_per_load=1)
        hd = io.HERAData(outfilename)
        d, f, n = hd.read(bls=[(53, 54, 'ee')])
        for bl in d:
            assert not np.all(np.isclose(d[bl], 0.))

        tfrfil = tfrf.TophatFRFilter(uvh5, filetype='uvh5')
        tfrfil.read(bls=[(53, 54, 'ee')])
        tfrfil.run_tophat_frfilter(to_filter=[(53, 54, 'ee')], tol=1e-4, verbose=True)
        np.testing.assert_almost_equal(d[(53, 54, 'ee')], tfrfil.clean_resid[(53, 54, 'ee')], decimal=5)
        np.testing.assert_array_equal(f[(53, 54, 'ee')], tfrfil.flags[(53, 54, 'ee')])
        # test NotImplementedError
        pytest.raises(NotImplementedError, tfrf.load_tophat_frfilter_and_write, uvh5, res_outfilename=outfilename, tol=1e-4,
                      clobber=True, Nbls_per_load=1, avg_red_bllens=True, baseline_list=[(54, 54, 'ee')])

        # test loading and writing all baselines at once.
        uvh5 = os.path.join(DATA_PATH, "test_input/zen.2458101.46106.xx.HH.OCR_53x_54x_only.uvh5")
        outfilename = os.path.join(tmp_path, 'temp.h5')
        for avg_bl in [True, False]:
            tfrf.load_tophat_frfilter_and_write(uvh5, res_outfilename=outfilename, tol=1e-4, clobber=True,
                                                Nbls_per_load=None, avg_red_bllens=avg_bl)
            hd = io.HERAData(outfilename)
            d, f, n = hd.read(bls=[(53, 54, 'ee')])
            for bl in d:
                assert not np.all(np.isclose(d[bl], 0.))

        tfrfil = tfrf.TophatFRFilter(uvh5, filetype='uvh5')
        tfrfil.read(bls=[(53, 54, 'ee')])
        tfrfil.run_tophat_frfilter(to_filter=[(53, 54, 'ee')], tol=1e-4, verbose=True)
        np.testing.assert_almost_equal(d[(53, 54, 'ee')], tfrfil.clean_resid[(53, 54, 'ee')], decimal=5)
        np.testing.assert_array_equal(f[(53, 54, 'ee')], tfrfil.flags[(53, 54, 'ee')])

        cal = os.path.join(DATA_PATH, "test_input/zen.2458101.46106.xx.HH.uv.abs.calfits_54x_only")
        outfilename = os.path.join(tmp_path, 'temp.h5')
        os.remove(outfilename)
        for avg_bl in [True, False]:
            tfrf.load_tophat_frfilter_and_write(uvh5, calfile_list=cal, tol=1e-4, res_outfilename=outfilename,
                                                Nbls_per_load=2, clobber=True, avg_red_bllens=avg_bl)
            hd = io.HERAData(outfilename)
            assert 'Thisfilewasproducedbythefunction' in hd.history.replace('\n', '').replace(' ', '')
            d, f, n = hd.read()
            for bl in d:
                if not np.all(f[bl]):
                    assert not np.all(np.isclose(d[bl], 0.))
            np.testing.assert_array_equal(f[(53, 54, 'ee')], True)
            os.remove(outfilename)

        # prepare an input file for broadcasting flags
        input_file = os.path.join(tmp_path, 'temp_special_flags.h5')
        shutil.copy(uvh5, input_file)
        hd = io.HERAData(input_file)
        _, flags, _ = hd.read()
        ntimes_before = hd.Ntimes
        nfreqs_before = hd.Nfreqs
        freqs_before = hd.freqs
        times_before = hd.times
        for bl in flags:
            flags[bl][:] = False
            flags[bl][0, :hd.Nfreqs // 2] = True  # first time has 50% flagged
            flags[bl][-3:, -1] = True  # last channel has flags for three integrations
        hd.update(flags=flags)
        hd.write_uvh5(input_file, clobber=True)
        # this time_threshold will result in
        # entire first integration begin flagged
        # and entire final channel being flagged
        # when flags are broadcasted.
        time_thresh = 2. / hd.Ntimes
        tfrf.load_tophat_frfilter_and_write(input_file, res_outfilename=outfilename, tol=1e-4,
                                            factorize_flags=True, time_thresh=time_thresh, clobber=True)
        hd = io.HERAData(outfilename)
        d, f, n = hd.read(bls=[(53, 54, 'ee')])
        for bl in f:
            assert np.any(f[bl][:, :-1])
            assert np.all(f[bl][0, :])

        # test delay filtering and writing with factorized flags and partial i/o
        tfrf.load_tophat_frfilter_and_write(input_file, res_outfilename=outfilename, tol=1e-4,
                                            factorize_flags=True, time_thresh=time_thresh, clobber=True)
        hd = io.HERAData(outfilename)
        d, f, n = hd.read(bls=[(53, 54, 'ee')])
        for bl in f:
            # check that flags were broadcasted.
            assert np.all(f[bl][0, :])
            assert np.all(f[bl][:, -1])
            assert not np.all(np.isclose(d[bl], 0.))

        tfrf.load_tophat_frfilter_and_write(input_file, res_outfilename=outfilename, tol=1e-4, Nbls_per_load=1,
                                            factorize_flags=True, time_thresh=time_thresh, clobber=True)
        hd = io.HERAData(outfilename)
        d, f, n = hd.read(bls=[(53, 54, 'ee')])
        for bl in f:
            # check that flags were broadcasted.
            assert np.all(f[bl][0, :])
            assert np.all(f[bl][:, -1])
            assert not np.all(np.isclose(d[bl], 0.))

        # test apriori flags and flag_yaml
        hd = io.HERAData(uvh5)
        hd.read()
        flag_yaml = os.path.join(DATA_PATH, 'test_input/a_priori_flags_sample.yaml')
        uvf = UVFlag(hd, mode='flag', copy_flags=True)
        uvf.to_waterfall(keep_pol=False, method='and')
        uvf.flag_array[:] = False
        flagfile = os.path.join(tmp_path, 'test_flag.h5')
        uvf.write(flagfile, clobber=True)
        tfrf.load_tophat_frfilter_and_write(uvh5, res_outfilename=outfilename,
                                            Nbls_per_load=1, clobber=True, mode='dayenu',
                                            external_flags=flagfile,
                                            overwrite_flags=True)
        # test that all flags are False
        hd = io.HERAData(outfilename)
        d, f, n = hd.read(bls=[(53, 54, 'ee')])
        for k in f:
            assert np.all(~f[k])
        # now without parital io.
        tfrf.load_tophat_frfilter_and_write(uvh5, res_outfilename=outfilename,
                                            clobber=True, mode='dayenu',
                                            external_flags=flagfile,
                                            overwrite_flags=True)
        # test that all flags are False
        hd = io.HERAData(outfilename)
        d, f, n = hd.read(bls=[(53, 54, 'ee')])
        for k in f:
            assert np.all(~f[k])

    def test_load_dayenu_filter_and_write(self, tmpdir):
        tmp_path = tmpdir.strpath
        uvh5 = os.path.join(DATA_PATH, "test_input/zen.2458101.46106.xx.HH.OCR_53x_54x_only.uvh5")
        cdir = os.path.join(tmp_path, 'cache_temp')
        # make a cache directory
        if os.path.isdir(cdir):
            shutil.rmtree(cdir)
        os.mkdir(cdir)
        outfilename = os.path.join(tmp_path, 'temp.h5')
        # run dayenu filter
        avg_bl = True
        tfrf.load_tophat_frfilter_and_write(uvh5, res_outfilename=outfilename,
                                            cache_dir=cdir, mode='dayenu',
                                            Nbls_per_load=1, clobber=True, avg_red_bllens=avg_bl,
                                            spw_range=(0, 32), write_cache=True)
        # generate duplicate cache files to test duplicate key handle for cache load.
        tfrf.load_tophat_frfilter_and_write(uvh5, res_outfilename=outfilename, cache_dir=cdir,
                                            mode='dayenu', avg_red_bllens=avg_bl,
                                            Nbls_per_load=1, clobber=True, read_cache=False,
                                            spw_range=(0, 32), write_cache=True)
        # there should now be six cache files (one per i/o/filter). There are three baselines.
        assert len(glob.glob(cdir + '/*')) == 6
        hd = io.HERAData(outfilename)
        assert 'Thisfilewasproducedbythefunction' in hd.history.replace('\n', '').replace(' ', '')
        d, f, n = hd.read(bls=[(53, 54, 'ee')])
        np.testing.assert_array_equal(f[(53, 54, 'ee')], True)
        os.remove(outfilename)
        shutil.rmtree(cdir)
        os.mkdir(cdir)
        # now do all the baselines at once.
        for avg_bl in [True, False]:
            tfrf.load_tophat_frfilter_and_write(uvh5, res_outfilename=outfilename,
                                                cache_dir=cdir, mode='dayenu', avg_red_bllens=avg_bl,
                                                Nbls_per_load=None, clobber=True,
                                                spw_range=(0, 32), write_cache=True)
            if avg_bl:
                assert len(glob.glob(cdir + '/*')) == 1
            hd = io.HERAData(outfilename)
            assert 'Thisfilewasproducedbythefunction' in hd.history.replace('\n', '').replace(' ', '')
            d, f, n = hd.read(bls=[(53, 54, 'ee')])
            np.testing.assert_array_equal(f[(53, 54, 'ee')], True)
            os.remove(outfilename)
        shutil.rmtree(cdir)
        os.mkdir(cdir)
        # run again using computed cache.
        calfile = os.path.join(DATA_PATH, "test_input/zen.2458101.46106.xx.HH.uv.abs.calfits_54x_only")
        tfrf.load_tophat_frfilter_and_write(uvh5, res_outfilename=outfilename, max_frate_coeffs=[0.0, 0.025],
                                            cache_dir=cdir, calfile_list=calfile, read_cache=True,
                                            Nbls_per_load=1, clobber=True, mode='dayenu',
                                            spw_range=(0, 32), write_cache=True)
        # no new cache files should be generated.
        assert len(glob.glob(cdir + '/*')) == 1
        hd = io.HERAData(outfilename)
        assert 'Thisfilewasproducedbythefunction' in hd.history.replace('\n', '').replace(' ', '')
        d, f, n = hd.read(bls=[(53, 54, 'ee')])
        np.testing.assert_array_equal(f[(53, 54, 'ee')], True)
        os.remove(outfilename)
        shutil.rmtree(cdir)

    def test_tophat_clean_argparser(self):
        sys.argv = [sys.argv[0], 'a', '--clobber', '--window', 'blackmanharris', '--max_frate_coeffs', '0.024', '-0.229']
        parser = tfrf.tophat_frfilter_argparser()
        a = parser.parse_args()
        assert a.datafilelist == ['a']
        assert a.clobber is True
        assert a.window == 'blackmanharris'
        assert a.max_frate_coeffs[0] == 0.024
        assert a.max_frate_coeffs[1] == -0.229
        assert a.time_thresh == 0.05
        assert not a.factorize_flags

    def test_tophat_linear_argparser(self):
        sys.argv = [sys.argv[0], 'a', '--clobber', '--write_cache', '--cache_dir', '/blah/', '--max_frate_coeffs', '0.024', '-0.229']
        parser = tfrf.tophat_frfilter_argparser(mode='dayenu')
        a = parser.parse_args()
        assert a.datafilelist == ['a']
        assert a.clobber is True
        assert a.write_cache is True
        assert a.cache_dir == '/blah/'
        assert a.max_frate_coeffs[0] == 0.024
        assert a.max_frate_coeffs[1] == -0.229
        assert a.time_thresh == 0.05
        assert not a.factorize_flags
        parser = tfrf.tophat_frfilter_argparser(mode='dpss_leastsq')
        a = parser.parse_args()
        assert a.datafilelist == ['a']
        assert a.clobber is True
        assert a.write_cache is True
        assert a.cache_dir == '/blah/'
        assert a.max_frate_coeffs[0] == 0.024
        assert a.max_frate_coeffs[1] == -0.229
        assert a.time_thresh == 0.05
        assert not a.factorize_flags